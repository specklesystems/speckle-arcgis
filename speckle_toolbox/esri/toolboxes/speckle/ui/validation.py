
from typing import Union
from specklepy.api.wrapper import StreamWrapper
from specklepy.api.models import Stream, Branch, Commit 
from specklepy.transports.server import ServerTransport
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException, GraphQLException

import arcpy 
try:
    from speckle.plugin_utils.logger import logToUser
except:
    from speckle_toolbox.esri.toolboxes.speckle.plugin_utils.logger import logToUser
  
def tryGetStream (sw: StreamWrapper) -> Union[Stream, None]:
    try:
        client = sw.get_client()
        stream = client.stream.get(id = sw.stream_id, branch_limit = 100, commit_limit = 100)
        if isinstance(stream, GraphQLException):
            raise SpeckleException(stream.errors[0]['message'])
        return stream
    except Exception as e: 
        logToUser(str(e)) 
        return None 

def validateStream(streamWrapper: StreamWrapper) -> Union[Stream, None]:
    try: 
        stream = tryGetStream(streamWrapper)
        if isinstance(stream, SpeckleException): return None

        if stream.branches is None:
            logToUser("Stream has no branches")
            return None
        return stream
    except Exception as e:
        logToUser(e)
        return None


def validateBranch(stream: Stream, branchName: str, checkCommits: bool) ->  Union[Branch, None]:
    try:
        branch = None
        if not stream.branches or not stream.branches.items: 
            return None
        for b in stream.branches.items:
            if b.name == branchName:
                branch = b
                break
        if branch is None: 
            logToUser("Failed to find a branch")
            return None
        if checkCommits == True:
            if branch.commits is None:
                logToUser("Failed to find a branch")
                return None
            if len(branch.commits.items)==0:
                logToUser("Branch contains no commits")
                return None
        return branch
    
    except Exception as e: 
        logToUser(str(e)) 
        return None
                
def validateCommit(branch: Branch, commitId: str) -> Union[Commit, None]:
    try:
        commit = None
        try: commitId = commitId.split(" | ")[0]
        except: logToUser("Commit ID is not valid")

        for i in branch.commits.items:
            if i.id == commitId:
                commit = i
                break
        if commit is None:
            try: 
                commit = branch.commits.items[0]
                logToUser("Failed to find a commit. Receiving Latest")
            except: 
                logToUser("Failed to find a commit")
                return None
        return commit
    except Exception as e:
        logToUser(e)

def validateTransport(client: SpeckleClient, streamId: str) -> Union[ServerTransport, None]:
    try: 
        transport = ServerTransport(client=client, stream_id=streamId)
        return transport
    except Exception as e: 
        logToUser("Make sure you have sufficient permissions: " + str(e))
        return None
