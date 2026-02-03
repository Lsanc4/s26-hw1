# Allowed Modules
import logging
import socket
import sys
import gzip 
import ssl
# End of Allowed Modules
# Adding any extra module will result into score of 0

def retrieve_url(url):
    """
    return bytes of the body of the document at url
    """

    return b"this is unlikely to be correct"

if __name__ == "__main__":
    sys.stdout.buffer.write(retrieve_url(sys.argv[1]))
