from flask_sqlalchemy import SQLAlchemy

database = SQLAlchemy()


class ElectionParticipant(database.Model):
    __tablename__ = 'election_participant'

    id = database.Column(database.Integer, primary_key=True)
    electionId = database.Column(database.Integer, database.ForeignKey('election.id'), nullable=False)
    participantId = database.Column(database.Integer, database.ForeignKey('participant.id'), nullable=False)


class Participant(database.Model):
    __tablename__ = 'participant'

    id = database.Column(database.Integer, primary_key=True)
    name = database.Column(database.String(256), nullable=False)
    individual = database.Column(database.Boolean, nullable=False)
    result = database.Column(database.Float)

    elections = database.relationship('Election', secondary=ElectionParticipant.__table__,
                                      back_populates='participants')

    def serialize(self):
        return dict(name=self.name, individual=self.individual, id=self.id)

    def serialize_short(self):
        return dict(id=self.id, name=self.name)


class Election(database.Model):
    __tablename__ = 'election'

    id = database.Column(database.Integer, primary_key=True)
    start = database.Column(database.DateTime, nullable=False)
    end = database.Column(database.DateTime, nullable=False)
    individual = database.Column(database.Boolean, nullable=False)

    participants = database.relationship('Participant', secondary=ElectionParticipant.__table__,
                                         back_populates='elections')

    votes = database.relationship('Vote')

    def __repr__(self):
        return str(dict(id=self.id, start=str(self.start), end=str(self.end), individual=self.individual,
                        participants=self.participants))

    def serialize(self):
        return dict(id=self.id, start=str(self.start), end=str(self.end), individual=self.individual,
                    participants=[p.serialize_short() for p in self.participants])


class Vote(database.Model):
    __tablename__ = 'vote'

    id = database.Column(database.Integer, primary_key=True)
    guid = database.Column(database.String(40), nullable=False)
    officialJMBG = database.Column(database.String(13), nullable=False)
    pollNumber = database.Column(database.Integer, nullable=False)

    invalid = database.Column(database.Boolean, nullable=False, default=False)
    reason = database.Column(database.String(64))

    electionId = database.Column(database.Integer, database.ForeignKey('election.id'), nullable=False)

    def __repr__(self):
        return str(dict(ballotGuid=self.guid, electionOfficialJmbg=self.officialJMBG, pollNumber=self.pollNumber,
                        invalid=self.invalid, reason=self.reason))
