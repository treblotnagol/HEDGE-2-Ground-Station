import ax25
import kiss
import socket

UNPROTO_FRAME_TYPE = ax25.FrameType.UI
UNPROTO_PID = 0xF0

def create_ui_frame(call_from, call_to, message):
    """
    Create a UI frame from the provided arguments. The message is text, and
    so must be encoded into a byte sequence for the AX.25 frame.
    """
    return ax25.Frame(
        call_to,
        call_from,
        control=ax25.Control(UNPROTO_FRAME_TYPE),
        pid=UNPROTO_PID,
        data=message)


def send_unproto(host, port, frame):
    """
    Connect to the server and send the provided content as a KISS frame. The
    KISS encoding is encapsulated within the send_data() method, so we simply
    need to pass the packed AX.25 frame to it. Note that no receive callback
    is provided to the connection, since we are not interested in incoming
    packets.
    """
    connection = kiss.Connection(None)
    error = None
    try:
        connection.connect_to_server(host, int(port))
    except socket.gaierror as e:
        if e.errno == socket.EAI_NONAME:
            error = 'Server name not found'
        else:
            error = 'Invalid server address'
    except ConnectionRefusedError:
        error = 'Connection refused by server'
    except Exception:
        error = 'Unknown error connecting to server'
    else:
        connection.send_data(frame.pack())
        connection.disconnect_from_server()

    return error

