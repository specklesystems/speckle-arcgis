
from typing import Union
from specklepy.api.wrapper import StreamWrapper
from specklepy.api.models import Stream, Branch, Commit 
from specklepy.transports.server import ServerTransport
from specklepy.api.client import SpeckleClient
from specklepy.logging.exceptions import SpeckleException, GraphQLException

import inspect 

import arcpy 
try:
    from speckle.speckle.ui.logger import logToUser
except:
    from speckle_toolbox.esri.toolboxes.speckle.speckle.ui.logger import logToUser

def tryGetStream(
    sw: StreamWrapper, dataStorage, write=False, dockwidget=None
) -> Union[Stream, None]:
    try:
        # print("tryGetStream")
        client, stream = tryGetClient(sw, dataStorage, write, dockwidget)
        return stream
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=dockwidget)
        return None


def tryGetClient(sw: StreamWrapper, dataStorage, write=False, dockwidget=None):
    # only streams with write access
    try:
        client = None
        savedRole = None
        savedStreamId = None
        for acc in dataStorage.accounts:
            # only check accounts on selected server
            if acc.serverInfo.url in sw.server_url:
                client = SpeckleClient(
                    acc.serverInfo.url, acc.serverInfo.url.startswith("https")
                )
                try:
                    client.authenticate_with_account(acc)
                    if client.account.token is not None:
                        break
                except SpeckleException as ex:
                    if "already connected" in ex.message:
                        logToUser(
                            "Dependencies versioning error.\nClick here for details.",
                            url="dependencies_error",
                            level=2,
                            plugin=dockwidget,
                        )
                        return
                    else:
                        raise ex

        # if token still not found
        if client is None or client.account.token is None:
            for acc in dataStorage.accounts:
                client = sw.get_client()
                if client is not None:
                    break

        if client is not None:
            stream = client.stream.get(
                id=sw.stream_id, branch_limit=100, commit_limit=100
            )
            if isinstance(stream, Stream):
                # print(stream.role)
                if write == False:
                    # try get stream, only read access needed
                    # print("only read access needed")
                    return client, stream
                else:
                    # check write access
                    # print("write access needed")
                    if stream.role is None or (
                        isinstance(stream.role, str) and "reviewer" in stream.role
                    ):
                        savedRole = stream.role
                        savedStreamId = stream.id
                    else:
                        return client, stream

        if savedRole is not None and savedStreamId is not None:
            logToUser(
                f"You don't have write access to the stream '{savedStreamId}'. You role is '{savedRole}'",
                level=2,
                func=inspect.stack()[0][3],
                plugin=dockwidget,
            )

        return None, None
    except Exception as e:
        logToUser(e, level=2, func=inspect.stack()[0][3], plugin=dockwidget)
        return None, None


def validateStream(stream: Stream, dockwidget) -> Union[Stream, None]:
    try: 
        if isinstance(stream, SpeckleException):
            return None

        if stream.branches is None:
            logToUser("Stream has no branches", level=1, plugin=dockwidget)
            return None
        return stream
    except Exception as e:
        logToUser(e, level=2, plugin=dockwidget)
        return


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
            logToUser("Failed to find a branch", level=2, func = inspect.stack()[0][3])
            return None
        if checkCommits == True:
            if branch.commits is None:
                logToUser("Failed to find a branch", level=2, func = inspect.stack()[0][3])
                return None
            if len(branch.commits.items)==0:
                logToUser("Branch contains no commits", level=2, func = inspect.stack()[0][3])
                return None
        return branch
    
    except Exception as e: 
        logToUser(str(e), level=2, func = inspect.stack()[0][3])
        return None
                
def validateCommit(branch: Branch, commitId: str) -> Union[Commit, None]:
    try:
        commit = None
        try: commitId = commitId.split(" | ")[0]
        except: logToUser("Commit ID is not valid", level=2, func = inspect.stack()[0][3])

        for i in branch.commits.items:
            if i.id == commitId:
                commit = i
                break
        if commit is None:
            try: 
                commit = branch.commits.items[0]
                logToUser("Failed to find a commit. Receiving Latest", level=2, func = inspect.stack()[0][3])
            except: 
                logToUser("Failed to find a commit", level=2, func = inspect.stack()[0][3])
                return None
        return commit
    except Exception as e:
        logToUser(str(e), level=2, func = inspect.stack()[0][3])

def validateTransport(client: SpeckleClient, streamId: str) -> Union[ServerTransport, None]:
    try: 
        transport = ServerTransport(client=client, stream_id=streamId)
        return transport
    except Exception as e: 
        logToUser("Make sure you have sufficient permissions: " + str(e), level=2, func = inspect.stack()[0][3])
        return None
