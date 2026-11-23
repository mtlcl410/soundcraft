from common import *
q='query { repository(owner:"storytold",name:"soundcraft"){pullRequest(number:1663){reviewThreads(first:100){nodes{id isResolved viewerCanResolve comments(first:2){nodes{databaseId author{login}}}}}}}}'
def readthreads():return api('graphql',payload={'query':q})['data']['repository']['pullRequest']['reviewThreads']['nodes']
original=json.loads((ev/'r5-before.json').read_text('utf-8-sig'))['data']['repository']['pullRequest']['reviewThreads']['nodes']
ids={x['id'] for x in original}
assert len(ids)==10
for x in readthreads():
 if x['id'] not in ids or x['isResolved']:continue
 assert x['viewerCanResolve'] and x['comments']['nodes'][0]['author']['login']=='coderabbitai'
 q2='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}'
 assert api('graphql',payload={'query':q2,'variables':{'id':x['id']}})['data']['resolveReviewThread']['thread']['isResolved']
rows=readthreads();save('r5-after.json',rows)
assert ids=={x['id'] for x in rows if x['id'] in ids and x['isResolved']}
print('10 original review threads resolved and verified')

