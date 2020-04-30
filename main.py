#  Copyright 2018 InfAI (CC SES)
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
import datetime
import os

from bson.objectid import ObjectId
from flask import Flask, request
from flask_restx import Api, Resource, fields, reqparse
from flask_cors import CORS
import json
import jwt
from pymongo import MongoClient, ReturnDocument, ASCENDING, DESCENDING

app = Flask("analytics-flow-repo")
app.config.SWAGGER_UI_DOC_EXPANSION = 'list'
CORS(app)
api = Api(app, version='0.1', title='Analytics Flow Repo API',
          description='Analytics Flow Repo API')


@api.route('/doc')
class Docs(Resource):
    def get(self):
        return api.__schema__


client = MongoClient(os.getenv('MONGO_ADDR', 'localhost'), os.getenv('MONGO_PORT', 27017))

db = client.flow_database

flows = db.flows

model = api.model('Model', {
    'cells': fields.Raw,
})

share = api.model('Share', {
    'list': fields.Boolean,
    'read': fields.Boolean,
    'write': fields.Boolean
})

flow_model = api.model('Flow', {
    'name': fields.String(required=True, description='Flow name'),
    'description': fields.String(required=True, description='Flow description'),
    'model': fields.Nested(model),
    'image': fields.String(required=False, description='Flow image'),
    'share': fields.Nested(share)
})

flow_return = flow_model.clone('Flow', {
    'userId': fields.String,
    '_id': fields.String(required=True, description='Flow id'),
    'dateCreated': fields.DateTime,
    'dateUpdated': fields.DateTime
})

flow_list = api.model('FlowList', {
    "flows": fields.List(fields.Nested(flow_return))
})

ns = api.namespace('flow', description='Operations related to flows')


@ns.route('', strict_slashes=False)
class Flow(Resource):
    @api.expect(flow_model)
    @api.marshal_with(flow_return, code=201)
    def put(self):
        """Creates a flow."""
        user_id = get_user_id(request)
        req = request.get_json()
        req['userId'] = user_id
        req['dateCreated'] = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        req['dateUpdated'] = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        flow_id = flows.insert_one(req).inserted_id
        f = flows.find_one({'_id': flow_id})
        print("Added flow: " + json.dumps({"_id": str(flow_id)}))
        return f, 201

    @api.marshal_with(flow_list, code=200)
    def get(self):
        """Returns a list of flows."""
        parser = reqparse.RequestParser()
        parser.add_argument('search', type=str, help='Search String', location='args')
        parser.add_argument('limit', type=int, help='Limit', location='args')
        parser.add_argument('offset', type=int, help='Offset', location='args')
        parser.add_argument('sort', type=str, help='Sort', location='args')
        args = parser.parse_args()
        limit = 0
        if not (args["limit"] is None):
            limit = args["limit"]
        offset = 0
        if not (args["offset"] is None):
            offset = args["offset"]
        if not (args["sort"] is None):
            sort = args["sort"].split(":")
        else:
            sort = ["name", "asc"]

        user_id = get_user_id(request)

        if not (args["search"] is None):
            if len(args["search"]) > 0:
                fs = flows.find({'$and': [{'name': {"$regex": args["search"]}}, {'userId': user_id}]}) \
                    .skip(offset).limit(limit) \
                    .sort("_id", 1).sort(sort[0], ASCENDING if sort[1] == "asc" else DESCENDING)
        else:
            fs = flows.find({'userId': user_id}) \
                .skip(offset).limit(limit).sort(sort[0], ASCENDING if sort[1] == "asc" else DESCENDING)
        flows_list = []
        for f in fs:
            flows_list.append(f)
        return {"flows": flows_list}


@ns.route('/<string:flow_id>', strict_slashes=False)
@api.response(404, 'Flow not found')
@ns.param('flow_id', 'The flow identifier')
class FlowMethods(Resource):
    @api.marshal_with(flow_return)
    def get(self, flow_id):
        """Get a flow."""
        user_id = get_user_id(request)
        f = flows.find_one({'$and': [{'_id': ObjectId(flow_id)}, {'userId': user_id}]})
        if f is not None:
            return f, 200
        return "Flow not found", 404

    @api.expect(flow_model)
    @api.marshal_with(flow_return)
    def post(self, flow_id):
        """Updates a flow."""
        user_id = get_user_id(request)
        req = request.get_json()
        req['dateUpdated'] = datetime.datetime.utcnow().replace(tzinfo=datetime.timezone.utc).isoformat()
        flow = flows.find_one_and_update({'$and': [{'_id': ObjectId(flow_id)}, {'userId': user_id}]}, {
            '$set': req,
        },
                                         return_document=ReturnDocument.AFTER)
        if flow is not None:
            return flow, 200
        return "Flow not found", 404

    @api.response(204, "Deleted")
    def delete(self, flow_id):
        """Deletes a flow."""
        user_id = get_user_id(request)
        f = flows.find_one({'$and': [{'_id': ObjectId(flow_id)}, {'userId': user_id}]})
        print(f)
        if f is not None:
            flows.delete_one({'_id': ObjectId(flow_id)})
            return "Deleted", 204
        return "Flow not found", 404


def get_user_id(req):
    user_id = req.headers.get('X-UserID')
    if user_id is None:
        user_id = jwt.decode(req.headers.get('Authorization')[7:], verify=False)['sub']
    if user_id is None:
        user_id = os.getenv('DUMMY_USER', 'admin')
    return user_id


if bool(os.getenv('DEBUG', '')):
    if __name__ == "__main__":
        app.run("0.0.0.0", 5000, debug=False)
else:
    if __name__ == "__main__":
        from waitress import serve
        serve(app, host="0.0.0.0", port=5000)
