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
#

import os
import typing

import requests
from werkzeug.datastructures import Authorization

url = os.getenv('OPERATOR_REPO_URL', 'localhost')


class OperatorIO(typing.TypedDict):
    name: str
    type: str


class Operator(typing.TypedDict, total=False):
    name: str
    image: typing.NotRequired[str]
    description: typing.NotRequired[str]
    pub: typing.NotRequired[bool]
    deploymentType: typing.NotRequired[str]
    inputs: typing.List[OperatorIO]
    outputs: typing.List[OperatorIO]
    cost: typing.NotRequired[int]
    config_values: typing.List[OperatorIO]


def get_operator(operator_id: str, user_id: str, auth_token: str = "") -> typing.Tuple[typing.Optional[Operator], int]:
    try:
        resp = requests.get(url + '/operator/' + operator_id, timeout=10, headers={'X-UserID' : user_id, 'Authorization' : auth_token})
    except requests.exceptions.RequestException as e:
        print(f"Error fetching operator {operator_id} for user {user_id} with exception {e}")
        return None, 502
    if resp.status_code != 200:
        return None, resp.status_code
    return resp.json(), 200
