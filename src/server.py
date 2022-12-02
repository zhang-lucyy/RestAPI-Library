from flask import Flask
from flask_restful import Resource, Api
from api.hello_world import HelloWorld
from api.users import Users

app = Flask(__name__)
api = Api(app)

api.add_resource(HelloWorld, '/')
api.add_resource(Users, '/users')

if __name__ == '__main__':
    app.run(debug=True)