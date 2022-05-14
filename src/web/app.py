import os
from flask import Flask, jsonify, request
from flask_restful import Api, Resource,fields
from pymongo import MongoClient
import bcrypt
import spacy
from flask_apispec import marshal_with,marshal_with, doc, use_kwargs
from flask_apispec.views import MethodResource
from marshmallow import Schema, fields
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin
from flask_apispec.extension import FlaskApiSpec


# Get environment variables
MONGO_HOST = os.getenv('MONGODB_HOSTNAME')
MONGO_USERNAME = os.getenv('MONGODB_USERNAME')
MONGO_PASSWORD = os.getenv('MONGODB_PASSWORD')
MONGO_PORT = os.getenv('MONGODB_PORT')

UTF8 = 'utf8'

app = Flask(__name__)
api = Api(app)

#Configure Swagger
app.config.update({
    'APISPEC_SPEC': APISpec(
        title='API Similarity Text',
        version='v1',
        plugins=[MarshmallowPlugin()],
        openapi_version='2.0.0'
    ),
    'APISPEC_SWAGGER_URL': '/swagger/',  # URI to access API Doc JSON 
    'APISPEC_SWAGGER_UI_URL': '/swagger-ui/'  # URI to access UI of API Doc
})
docs = FlaskApiSpec(app)



# Connect to Mongo
client = MongoClient(host=MONGO_HOST, port=MONGO_PORT, username=MONGO_USERNAME, password=MONGO_PASSWORD)

db = client.SimilarityDB
users = db['Users']

def user_exist(username):
    return users.count_documents({'Username': username}) > 0

def verify_pw(username, password):
    hashed_pw = users.find({
        'Username':username
    })[0]['Password']

    match_pwd = bcrypt.hashpw(password.encode(UTF8), hashed_pw) == hashed_pw
    return match_pwd

def count_tokens(username):
    tokens = users.find({
        'Username':username
    })[0]['Tokens']

    return tokens

#Schemas
class CommonResponseSchema(Schema):
    msg = fields.Str(default='Success')
    status = fields.Int(default=200)

class DetectResponseSchema(Schema):
    msg = fields.Str(default='Success')
    status = fields.Int(default=200)
    similarity = fields.String()

class RegisterRequestSchema(Schema):
    username = fields.String(required=True, description='User name to register')
    password = fields.String(required=True, description='Password to register')

class DetectRequestSchema(Schema):
    username = fields.String(required=True, description='User name to login')
    password = fields.String(required=True, description='Password to login')
    text1 = fields.String(required=True, description='Text one for comparison')
    text2 = fields.String(required=True, description='Text two for comparison')

class RefillRequestSchema(Schema):
    username = fields.String(required=True, description='User name to login')
    password = fields.String(required=True, description='Password to login')
    refill_amount = fields.Integer(required=True, description='Amount to fill tokens')


class Register(MethodResource, Resource):

    @doc(description='API to register a user', tags=['Register'])
    @use_kwargs(RegisterRequestSchema, location=('json'))
    @marshal_with(CommonResponseSchema)
    def post(self, **kwargs):
        #Step 1 is to get posted data by the user
        posted_data = request.get_json()

        #Get the data
        username = posted_data['username']
        password = posted_data['password']

        if user_exist(username):
            return {
                'status': 301,
                'msg': 'Invalid username'
            }


        hashed_pw = bcrypt.hashpw(password.encode(UTF8), bcrypt.gensalt())

        #Store username and pw into the database
        users.insert_one({
            'Username': username,
            'Password': hashed_pw,
            'Tokens':6
        })

        return {
            'status': 200,
            'msg': 'You have successfully signed up for the API'
        }


class Detect(MethodResource, Resource):
    @doc(description='API to detect text similarity', tags=['Detect'])
    @use_kwargs(DetectRequestSchema, location=('json'))
    @marshal_with(DetectResponseSchema)
    def post(self, **kwargs):
        posted_data = request.get_json()

        #Get the data
        username = posted_data['username']
        password = posted_data['password']
        text1 = posted_data['text1']
        text2 = posted_data['text2']

        if not user_exist(username):
            return {
                'status':301,
                'msg':'Invalid username'
            }

        correct_pw = verify_pw(username, password)

        if not correct_pw:
            return  {
                'status':302,
                'msg': 'Invalid password'
            }

        num_tokens = count_tokens(username)
        if num_tokens <= 0:
            return  {
                'status': 303,
                'msg': 'You are out of tokens, please refill your tokens'
            }

        #Calculate the edit distance
        nlp = spacy.load('en_core_web_sm')

        text1 = nlp(text1)
        text2 = nlp(text2)

        #Ration is a number between 0 and 1
        ratio = text1.similarity(text2)
        ratio_similarity =  round(ratio, 2) * 100
        return_json = {
            'status': 200,
            'similarity': str(ratio_similarity) + '%',
            'msg': 'Similarity score calculated successfully'
        }

        users.update_one({
            'Username':username
        }, {
            '$set':{
                'Tokens':num_tokens-1
                }
        })

        return return_json


api.add_resource(Register, '/register')
api.add_resource(Detect, '/detect')

docs.register(Register)
docs.register(Detect)

if __name__=='__main__':
    app.run(host='0.0.0.0')

