from flask import Flask, request, Response, jsonify
from configuration import Configuration
from flask_jwt_extended import JWTManager, get_jwt
from redis import Redis
import csv
import io
import json
from utils import role_check

application = Flask(__name__)
application.config.from_object(Configuration)

jwt = JWTManager(application)


@application.route('/vote', methods=['POST'])
@role_check('official')
def vote():
    file = request.files.get('file')
    if file is None:
        return jsonify(message='Field file is missing.'), 400

    additional_claims = get_jwt()
    jmbg = additional_claims['jmbg']

    votes = []

    stream = io.StringIO(file.stream.read().decode(encoding="utf8"))
    reader = csv.reader(stream)
    for i, single_vote in enumerate(reader):
        if len(single_vote) != 2:
            return jsonify(message=f'Incorrect number of values on line {str(i)}.'), 400
        try:
            single_vote[1] = int(single_vote[1])
        except ValueError:
            return jsonify(message=f'Incorrect poll number on line {str(i)}.'), 400
        if single_vote[1] <= 0:
            return jsonify(message=f'Incorrect poll number on line {str(i)}.'), 400

        vote_info = {'guid': single_vote[0], 'poll_number': single_vote[1]}
        votes.append(vote_info)

    votes_batch = {'jmbg': jmbg, 'votes': votes}

    with Redis(host=Configuration.REDIS_HOST) as redis:
        redis.publish(Configuration.REDIS_MESSAGE_CHANNEL, json.dumps(votes_batch))

    return Response(status=200)


if __name__ == '__main__':
    application.run(debug=True, host='0.0.0.0', port=5001)
