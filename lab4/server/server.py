# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group:29
# Student names: Pedro Mendes and Niklas Jonsson
# ------------------------------------------------------------------------------------------------------
# We import various libraries
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler  # Socket specifically designed to handle HTTP requests
import sys  # Retrieve arguments
from urlparse import parse_qs  # Parse POST data
from httplib import HTTPConnection  # Create a HTTP connection, as a client (for POST requests to the other vessels)
from urllib import urlencode  # Encode POST content into the HTTP header
from codecs import open  # Open a file
from threading import Thread  # Thread Management


# ------------------------------------------------------------------------------------------------------

# Global variables for HTML templates
try:
    vote_frontpage_template = open('server/vote_frontpage_template.html', 'r').read()
    vote_result_template = open('server/vote_result_template.html', 'r').read()
except Exception as e:
    print(e)

# ------------------------------------------------------------------------------------------------------
# Static variables definitions
PORT_NUMBER = 8080


# ------------------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
    # ------------------------------------------------------------------------------------------------------
    def __init__(self, server_address, handler, node_id, vessel_list):
        # We call the super init
        HTTPServer.__init__(self, server_address, handler)
        # our own ID (IP is 10.1.0.ID)
        self.vessel_id = vessel_id
        # The list of other vessels
        self.vessels = vessel_list

        self.vote = 0
        self.byzantine_votes = []
        self.byzantine_vectors = []
        self.byzantine = False

        self.votes = {}
        self.vectors = {}

        self.result = ""


        # ------------------------------------------------------------------------------------------------------
        # Contact a specific vessel with a set of variables to transmit to it

    def contact_vessel(self, vessel_ip, path, action, key, value):
        # the Boolean variable we will return
        success = False
        # The variables must be encoded in the URL format, through urllib.urlencode
        post_content = urlencode({'action': action, 'key': key, 'value': value})
        # the HTTP header must contain the type of data we are transmitting, here URL encoded
        headers = {"Content-type": "application/x-www-form-urlencoded"}
        # We should try to catch errors when contacting the vessel
        try:
            # We contact vessel:PORT_NUMBER since we all use the same port
            # We can set a timeout, after which the connection fails if nothing happened
            connection = HTTPConnection("%s:%d" % (vessel_ip, PORT_NUMBER), timeout=30)
            # We only use POST to send data (PUT and DELETE not supported)
            action_type = "POST"
            # We send the HTTP request
            connection.request(action_type, path, post_content, headers)
            # We retrieve the response
            response = connection.getresponse()
            # We want to check the status, the body should be empty
            status = response.status
            # If we receive a HTTP 200 - OK
            if status == 200:
                success = True
        # We catch every possible exceptions
        except Exception as e:
            print "Error while contacting %s" % vessel_ip
            # printing the error given by Python
            print(e)

        # we return if we succeeded or not
        return success

    # ------------------------------------------------------------------------------------------------------
    # We send a received value to all the other vessels of the system
    def propagate_value_to_vessels(self, path, action, key, value):
        # We iterate through the vessel list
        for vessel in self.vessels:
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != ("10.1.0.%s" % self.vessel_id):
                # A good practice would be to try again if the request failed
                # Here, we do it only once
                self.contact_vessel(vessel, path, action, key, value)

    #byzantine behaviour, here different votes might be sent to different vessels
    def byzantine_value_to_vessels(self, path, action, key, value):
        i = 0
        for vessel in self.vessels:
            if vessel != ("10.1.0.%s" % self.vessel_id):
                self.contact_vessel(vessel, path, action, key, value[i])
                i += 1


# ------------------------------------------------------------------------------------------------------





# ------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------
# This class implements the logic when a server receives a GET or POST request
# It can access to the server data through self.server.*
# i.e. the store is accessible through self.server.store
# Attributes of the server are SHARED accross all request hqndling/ threads!
class BlackboardRequestHandler(BaseHTTPRequestHandler):
    # ------------------------------------------------------------------------------------------------------
    # We fill the HTTP headers
    def set_HTTP_headers(self, status_code=200):
        # We set the response status code (200 if OK, something else otherwise)
        self.send_response(status_code)
        # We set the content type to HTML
        self.send_header("Content-type", "text/html")
        # No more important headers, we can close them
        self.end_headers()

    # ------------------------------------------------------------------------------------------------------
    # a POST request must be parsed through urlparse.parse_QS, since the content is URL encoded
    def parse_POST_request(self):
        post_data = ""
        # We need to parse the response, so we must know the length of the content
        length = int(self.headers['Content-Length'])
        # we can now parse the content using parse_qs
        post_data = parse_qs(self.rfile.read(length), keep_blank_values=1)
        # we return the data
        return post_data

    # Compute byzantine votes for round 1, by trying to create
    # a split decision.
    # input:
    #	number of loyal nodes,
    #	number of total nodes,
    #	Decision on a tie: True or False
    # output:
    #	A list with votes to send to the loyal nodes
    #	in the form [1,0,1,.....]
    def compute_byzantine_vote_round1(self, no_loyal, no_total, on_tie):
        result_vote = []
        for i in range(0, no_loyal):
            if i % 2 == 0:
                result_vote.append(1 - on_tie)
            else:
                result_vote.append(on_tie)
        return result_vote

    # Compute byzantine votes for round 2, trying to swing the decision
    # on different directions for different nodes.
    # input:
    #	number of loyal nodes,
    #	number of total nodes,
    #	Decision on a tie: True or False
    # output:
    #	A list where every element is a the vector that the
    #	byzantine node will send to every one of the loyal ones
    #	in the form [[1,...],[0,...],...]
    def compute_byzantine_vote_round2(self, no_loyal, no_total, on_tie):
        result_vectors = []
        for i in range(0, no_loyal):
            if i % 2 == 0:
                result_vectors.append(str(on_tie) * no_total)
            else:
                result_vectors.append(str(1 - on_tie) * no_total)
        return result_vectors

    # ------------------------------------------------------------------------------------------------------
    # ------------------------------------------------------------------------------------------------------
    # Request handling - GET
    # ------------------------------------------------------------------------------------------------------
    # This function contains the logic executed when this server receives a GET request
    # This function is called AUTOMATICALLY upon reception and is executed as a thread!
    def do_GET(self):
        print("Receiving a GET on path %s" % self.path)

        if self.path == '/vote/result':
            self.get_result()
        else:
            self.do_GET_Index()
        # ------------------------------------------------------------------------------------------------------
        # GET logic - specific path
        # ------------------------------------------------------------------------------------------------------

    def get_result(self):
        # We set the response status code to 200 (OK)
        self.set_HTTP_headers(200)

        #add the result string to the template
        result = vote_result_template % self.server.result
        self.wfile.write(result)

    def do_GET_Index(self):
        # We set the response status code to 200 (OK)
        self.set_HTTP_headers(200)

        #add the result string to the template
        result = vote_result_template % self.server.result
        html_response = vote_frontpage_template + result

        self.wfile.write(html_response)

    # ------------------------------------------------------------------------------------------------------



    # ------------------------------------------------------------------------------------------------------
    # Request handling - POST
    # ------------------------------------------------------------------------------------------------------
    def do_POST(self):
        print("Receiving a POST on %s" % self.path)
        # Here, we should check which path was requested and call the right logic based on it
        # We should also parse the data received
        # and set the headers for the client

        post_data = self.parse_POST_request()
        self.set_HTTP_headers(200)
        retransmit_round1 = False
        do_round2 = False

        #post from another vessel
        if 'action' in post_data:
            if ''.join(post_data['action']) == 'round1':
                #add the vote to a dict of votes
                key = int(''.join(post_data['key']))
                value = ''.join(post_data['value'])
                self.server.votes[key] = value

                if (len(self.server.votes) == len(self.server.vessels)):
                    retransmit_round1 = True

            elif ''.join(post_data['action']) == 'round2':
                #add the vector to a dict of vectors
                key = int(''.join(post_data['key']))
                #the values are represented by a string with length == number_of_vessels and 0, 1 for wait, attack
                #the first character in the string represents the vote of vessel number one, etc
                value = ''.join(post_data['value'])
                self.server.vectors[key] = value

                if len(self.server.vectors) == len(self.server.vessels):

                    do_round2 = True
        #post from own vessel
        else:
            #cast vote or assume byzantine behaviour
            if self.path == "/vote/attack":
                self.server.votes[self.server.vessel_id] = 1

            elif self.path == "/vote/retreat":
                self.server.votes[self.server.vessel_id] = 0

            elif self.path == "/vote/byzantine":
                self.server.byzantine = True
                self.server.byzantine_votes = self.compute_byzantine_vote_round1(2, 3, 1)
                self.server.votes[self.server.vessel_id] = 0

            #propagate the vote, or the byzantine behaviour
            if self.server.byzantine:
                thread = Thread(target=self.server.byzantine_value_to_vessels,
                                args=(self.path, 'round1', self.server.vessel_id, self.server.byzantine_votes))
                # We kill the process if we kill the server
                thread.daemon = True
                # We start the thread
                thread.start()
            else:
                thread = Thread(target=self.server.propagate_value_to_vessels,
                                args=(self.path, 'round1', self.server.vessel_id, self.server.vote))
                # We kill the process if we kill the server
                thread.daemon = True
                # We start the thread
                thread.start()

        # if all votes are cast, start round 2
        if retransmit_round1 == True:

            print("All votes cast, starting round 2")
            #add own vote vector to the dict
            myvotes = ""
            for i in range(1, len(self.server.votes) + 1):
                myvotes += str(self.server.votes[i])
            self.server.vectors[self.server.vessel_id] = myvotes

            # byzantine behaviour
            if self.server.byzantine:
                self.server.byzantine_vectors = self.compute_byzantine_vote_round2(2, 3, 1)

                # send own votes to other vessels
                thread = Thread(target=self.server.byzantine_value_to_vessels,
                                args=(self.path, 'round2', self.server.vessel_id, self.server.byzantine_vectors))
                thread.daemon = True
                thread.start()

            # honest behaviour
            else:
                # send own vector to other vessels
                thread = Thread(target=self.server.propagate_value_to_vessels,
                                args=(self.path, 'round2', self.server.vessel_id, myvotes))
                thread.daemon = True
                thread.start()

        #if all vectors are received, calculate and display result
        if do_round2 == True:

            do_round2 = False
            print("All vectors received, calculating result, vectors:" + str(len(self.server.vectors)) + " vessels:" + str(len(self.server.vessels)))
            self.server.result = ""
            finalattack = 0
            finalretreat = 0
            #create the string to display
            for key in range(1, len(self.server.vectors) + 1):
                print("Creating string")
                votes = ""

                for c in self.server.vectors[key]:
                    if c == "0":
                        votes += " Retreat"
                    else:
                        votes += " Attack"
                self.server.result += "Votes from vessel " + str(key) + ":" + votes + "\n"

            #calculate result
            for i in range(0, len(self.server.vectors)):
                print("Calculating result")
                attack = 0
                retreat = 0
                #compare the vote everyone received from vessel i
                for key in range(1, len(self.server.vectors) + 1):
                    #dont include what vote a vessel got from itself, unless there is only one vessel
                    if not i + 1 == key or len(self.server.vessels) == 1:
                        vector = self.server.vectors[key]
                        if vector[i] == "1":
                            attack += 1
                        else:
                            retreat += 1
                #add the result vote
                if attack >= retreat:
                    finalattack += 1
                else:
                    finalretreat += 1

            #add the final result to the string
            if finalattack >= finalretreat:
                self.server.result += "Result: Attack"
            else:
                self.server.result += "Result: Retreat"


# ------------------------------------------------------------------------------------------------------



# ------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------
# Execute the code
if __name__ == '__main__':

    ## read the templates from the corresponding html files
    # .....
    vessel_list = []
    vessel_id = 0
    # Checking the arguments
    if len(sys.argv) != 3:  # 2 args, the script and the vessel name
        print("Arguments: vessel_ID number_of_vessels")
    else:
        # We need to know the vessel IP
        vessel_id = int(sys.argv[1])
        # We need to write the other vessels IP, based on the knowledge of their number
        for i in range(1, int(sys.argv[2]) + 1):
            vessel_list.append("10.1.0.%d" % i)  # We can add ourselves, we have a test in the propagation


    # We launch a server
    server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, vessel_id, vessel_list)
    print("Starting the server on port %d" % PORT_NUMBER)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("Stopping Server")
# ------------------------------------------------------------------------------------------------------
