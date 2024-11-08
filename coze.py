from cozepy import Coze, TokenAuth, Stream, WorkflowEvent, WorkflowEventType
import json

TOKEN = 'pat_tEwF9lJLUedw7qGz7vn2ixEcCC8rMpDdC5joWLOu75q9VMV7TJ89jhLjfPhM40kF'
coze = Coze(auth=TokenAuth(TOKEN))


result = coze.workflows.runs.create(
    # id of workflow
    workflow_id='7433363425587281926',
    # params
    parameters={
        'name': "Фёдор",
        'age': 19,
        'descr': "1234",
    }
)

print(result)
a = json.loads(json.loads(result.json())["data"])['output']
print(a)
