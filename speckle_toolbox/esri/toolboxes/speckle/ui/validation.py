
from typing import Union
from specklepy.api.wrapper import StreamWrapper
from specklepy.api.models import Stream, Branch, Commit 
from specklepy.transports.server import ServerTransport
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException, GraphQLException

import arcpy 
  
def tryGetStream (sw: StreamWrapper) -> Stream:
    client = sw.get_client()
    stream = client.stream.get(id = sw.stream_id, branch_limit = 100, commit_limit = 100)
    if isinstance(stream, GraphQLException):
        raise SpeckleException(stream.errors[0]['message'])
    return stream

def validateStream(streamWrapper: StreamWrapper) -> Union[Stream, None]:
    try: 
        stream = tryGetStream(streamWrapper)
    except SpeckleException as e:
        arcpy.AddWarning(e.message)
        return None

    if isinstance(stream, SpeckleException): return None

    if stream.branches is None:
        arcpy.AddWarning("Stream has no branches")
        return None
    return stream

def validateBranch(stream: Stream, branchName: str, checkCommits: bool) ->  Union[Branch, None]:
    branch = None
    if not stream.branches or not stream.branches.items: 
      return None
    for b in stream.branches.items:
        if b.name == branchName:
            branch = b
            break
    if branch is None: 
        arcpy.AddWarning("Failed to find a branch")
        return None
    if checkCommits == True:
        if branch.commits is None:
            arcpy.AddWarning("Failed to find a branch")
            return None
        if len(branch.commits.items)==0:
            arcpy.AddWarning("Branch contains no commits")
            return None
    return branch
            
def validateCommit(branch: Branch, commitId: str) -> Union[Commit, None]:
    commit = None
    try: commitId = commitId.split(" | ")[0]
    except: arcpy.AddWarning("Commit ID is not valid")

    for i in branch.commits.items:
        if i.id == commitId:
            commit = i
            break
    if commit is None:
        try: 
            commit = branch.commits.items[0]
            arcpy.AddWarning("Failed to find a commit. Receiving Latest")
        except: 
            arcpy.AddWarning("Failed to find a commit")
            return None
    return commit

def validateTransport(client: SpeckleClient, streamId: str) -> Union[ServerTransport, None]:
    try: transport = ServerTransport(client=client, stream_id=streamId)
    except Exception as e: 
        arcpy.AddWarning("Make sure you have sufficient permissions: " + str(e))
        return None
    return transport
