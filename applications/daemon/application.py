from _datetime import datetime, timedelta
from flask import Flask
from configuration import Configuration
from models import database, Vote, Election, Participant
from redis import Redis
from sqlalchemy import and_
import json

application = Flask(__name__)
application.config.from_object(Configuration)

with application.app_context() as context:
    database.init_app(application)
    with Redis(host=Configuration.REDIS_HOST) as redis:

        channel = redis.pubsub()
        channel.subscribe(Configuration.REDIS_MESSAGE_CHANNEL)

        while True:
            message = channel.get_message()
            if message is not None and message['data'] != 1:
                now = datetime.now()  # + timedelta(seconds=1)

                election = Election.query.filter(and_(Election.start <= now, Election.end >= now)).first()
                if election is not None:
                    batch = json.loads(message['data'].decode("utf-8"))
                    jmbg = batch.get('jmbg')

                    votes = []
                    for vote in batch.get('votes'):
                        guid = vote.get('guid')
                        checked_vote = None
                        poll_number = vote.get('poll_number')

                        if Vote.query.filter(Vote.guid == guid).first() is not None:
                            checked_vote = Vote(guid=guid, officialJMBG=jmbg, electionId=election.id,
                                                pollNumber=poll_number, invalid=True, reason='Duplicate ballot.')
                        elif poll_number > len(election.participants):
                            checked_vote = Vote(guid=guid, officialJMBG=jmbg, electionId=election.id,
                                                pollNumber=poll_number, invalid=True, reason='Invalid poll number.')
                        else:
                            checked_vote = Vote(guid=guid, officialJMBG=jmbg, electionId=election.id,
                                                pollNumber=poll_number, invalid=False, reason=None)

                        database.session.add(checked_vote)
                        database.session.commit()
