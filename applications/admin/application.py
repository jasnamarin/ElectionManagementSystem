from flask import Flask, request, jsonify
from flask_jwt_extended import JWTManager
from applications.models import database, Participant, Election, ElectionParticipant, Vote
from applications.configuration import Configuration
from sqlalchemy import or_, and_
from applications.utils import role_check
from dateutil.parser import isoparse
import numpy as np
from datetime import datetime, timedelta

application = Flask(__name__)
application.config.from_object(Configuration)

jwt = JWTManager(application)


@application.route('/createParticipant', methods=['POST'])
@role_check('admin')
def register():
    message = None
    name = request.json.get('name', '')
    if name is None or len(name) == 0:
        message = 'Field name is missing.'
    individual = request.json.get('individual', '')
    if message is None and (individual is None or individual == ''):
        message = 'Field individual is missing.'

    if message is not None:
        return jsonify(message=message), 400

    participant = Participant(name=name, individual=individual)
    database.session.add(participant)
    database.session.commit()

    return jsonify(id=participant.id), 200


@application.route('/getParticipants', methods=['GET'])
@role_check('admin')
def getParticipants():
    participants = Participant.query.all()
    participants_list = [participant.serialize() for participant in participants]
    return jsonify(participants=participants_list), 200


@application.route('/createElection', methods=['POST'])
@role_check('admin')
def createElection():
    start = request.json.get('start', '')
    end = request.json.get('end', '')
    individual = request.json.get('individual', '')
    participants = request.json.get('participants', '')

    message = None
    if start is None or len(start) == 0:
        message = 'Field start is missing.'
    elif end is None or len(end) == 0:
        message = 'Field end is missing.'
    elif individual is None or individual == '':
        message = 'Field individual is missing.'
    elif participants is None or participants == '':
        message = 'Field participants is missing.'

    if message is not None:
        return jsonify(message=message), 400

    try:
        start = isoparse(start)
        end = isoparse(end)

        if end <= start or Election.query.filter(or_(or_(and_(Election.start <= start, Election.end >= start),
                                                         and_(Election.start <= end, Election.end >= end)),
                                                     and_(Election.start >= start, Election.end <= end))).first():
            message = 'Invalid date and time.'
    except ValueError:
        message = 'Invalid date and time.'

    if message is not None:
        return jsonify(message=message), 400

    if len(participants) < 2:
        message = 'Invalid participants.'
    else:
        for p in participants:
            participant = Participant.query.filter(Participant.id == p).first()
            if participant is None:
                message = 'Invalid participants.'
                break
            if participant.individual != individual:
                message = 'Invalid participants.'
                break

    if message is not None:
        return jsonify(message=message), 400

    election = Election(start=start, end=end, individual=individual)
    database.session.add(election)
    database.session.commit()

    for participant in participants:
        election_participant = ElectionParticipant(electionId=election.id, participantId=participant)
        database.session.add(election_participant)
        database.session.commit()
    poll_numbers = [i for i in range(1, len(participants) + 1)]

    return jsonify(pollNumbers=poll_numbers), 200


@application.route('/getElections', methods=['GET'])
@role_check('admin')
def getElections():
    elections = Election.query.all()
    elections_list = [election.serialize() for election in elections]
    return jsonify(elections=elections_list), 200


@application.route('/getResults', methods=['GET'])
@role_check('admin')
def getResults():
    election_id = request.args.get('id')
    if election_id is None:
        return jsonify(message='Field id is missing.'), 400

    message = None
    election = Election.query.filter(Election.id == election_id).first()
    if election is None:
        message = 'Election does not exist.'
    elif datetime.now() < election.end:  # + timedelta(seconds=3)
        message = 'Election is ongoing.'

    if message is not None:
        return jsonify(message=message), 400

    invalid_votes = [dict(electionOfficialJmbg=vote.officialJMBG, ballotGuid=vote.guid, pollNumber=vote.pollNumber,
                          reason=vote.reason)
                     for vote in Vote.query.filter(and_(Vote.electionId == election.id, Vote.invalid == True)).all()]

    valid_votes = Vote.query.filter(and_(Vote.electionId == election.id, Vote.invalid == False)).all()

    participant_votes = {}
    for vote in valid_votes:
        if vote.pollNumber - 1 in participant_votes.keys():
            participant_votes[vote.pollNumber - 1] += 1
        else:
            participant_votes[vote.pollNumber - 1] = 1

    if election.individual is True:
        participant_results = {key: round(value / len(valid_votes), 2) for key, value in participant_votes.items()}
    else:
        seats = [0] * len(election.participants)
        min_votes = int(len(valid_votes) * 0.05)
        quot = [0] * len(election.participants)
        for i, votes in participant_votes.items():
            if votes < min_votes:
                participant_votes[i] = 0
            quot[i] = participant_votes[i]
        for i in range(250):
            k = np.argmax(quot)
            seats[k] += 1
            for key in participant_votes.keys():
                quot[key] = participant_votes[key] / (seats[key] + 1)
        participant_results = {}
        for key, _ in participant_votes.items():
            participant_results[key] = seats[key]

    participants = []
    for i in participant_results.keys():
        poll_number = i + 1
        participants.append(dict(pollNumber=poll_number, name=election.participants[i].name,
                                 result=participant_results[i]))

    return jsonify(participants=participants, invalidVotes=invalid_votes), 200


if __name__ == '__main__':
    database.init_app(application)
    application.run(debug=True, host='0.0.0.0', port=5000)
