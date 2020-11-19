# coding=utf-8
# ------------------------------------------------------------------------------------------------------
# TDA596 Labs - Server Skeleton
# server/server.py
# Input: Node_ID total_number_of_ID
# Student Group:29
# Student names:Pedro Mendes and Niklas Jonsson
# ------------------------------------------------------------------------------------------------------
#       Import various libraries
# -----------------------------------------------------------------------------------------------------
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler  # Socket specifically designed to handle HTTP requests
import sys  # Retrieve arguments
from urlparse import parse_qs  # Parse POST data
from httplib import HTTPConnection  # Create a HTTP connection, as a client (for POST requests to the other vessels)
from urllib import urlencode  # Encode POST content into the HTTP header
from codecs import open  # Open a file
from threading import Thread, Lock  # Thread Management
from time import sleep, time
from operator import attrgetter
from threading import Lock
# ------------------------------------------------------------------------------------------------------


# ----------------------------------------------------------------------------------------------------
#       Protocols of communications - actions
# ----------------------------------------------------------------------------------------------------
                                                            #
#submit (add) a new post on a blackboard                    #
add_post = "submit_new_post"                                #
                                                            #
#modify one post on a blackboard                            #
modi_post = "modify_post"                                   #
                                                            #
#delete one post on a blackboard                            #
del_post = "delete_post"                                    #
                                                            #
#update a information id on a blackboard                    #
update_id = "update_new_id"                                 #
                                                            #
# ------------------------------------------------------------------------------------------------------



# ------------------------------------------------------------------------------------------------------
#       Global variables for HTML templates
# ------------------------------------------------------------------------------------------------------
try:
    board_frontpage_footer_template = open('server/board_frontpage_footer_template.html', 'r').read()
    board_frontpage_header_template = open('server/board_frontpage_header_template.html', 'r').read()
    boardcontents_template = open('server/boardcontents_template.html', 'r').read()
    entry_template = open('server/entry_template.html', 'r').read()
except Exception as e:
    print(e)
# ------------------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------------------
#       Static variables definitions
# ------------------------------------------------------------------------------------------------------
PORT_NUMBER = 8080

# ------------------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------------------
#       Global variables definitions
# ------------------------------------------------------------------------------------------------------
global counter
global num_messages

# ------------------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------------------
#       Locks
# ------------------------------------------------------------------------------------------------------
mutex = Lock()
mutex_list = Lock()
# ------------------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------------------
#       Class of a message
# ------------------------------------------------------------------------------------------------------
class Message:
    def __init__(self, uniqueid, message, idi):
        #unique id - doesn't change during all the execution
        self.uniqueid = uniqueid
        #data post
        self.message = message
        #seq. number
        self.id = idi
        #store action in the waiting actions list
        self.action = None
# ------------------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------------------
#       Class blackboard server
# ------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
# ------------------------------------------------------------------------------------------------------
    def __init__(self, server_address, handler, node_id, vessel_list):
        # We call the super init
        HTTPServer.__init__(self, server_address, handler)
        # we create the list of values
        self.store = []
        # We keep a variable of the next id to insert
        self.current_key = -1
        # our own ID (IP is 10.1.0.ID)
        self.vessel_id = vessel_id
        # The list of other vessels
        self.vessels = vessel_list
        #list of action in a waiting list
        self.wait_list = []

# ------------------------------------------------------------------------------------------------------
    # We add a value received to the store
    def add_value_to_store_new(self, m):
        # We add the value to the store
        # next id
        self.current_key = self.current_key + 1
        idi = self.current_key
        ip = self.vessel_id

        # store in the dict
        message = ''.join(m)

        #uni_id: varible that stores an unique id that doesn't change during all the program
        #this is form by two numbers: the host id of Ip address(last number) and seq.number (current_key)
        #the first  numbers are form the seq.munber and the lat two numbers are from the IP
        #uni_id = [ seq.number | IP ]
        #by our choice of simplification, we assume that the maximum number of nodes are 100, which for the simulation
        #using the mininet is perfect resonable, but if we for some way needed more node we could easly change this part
        #of the code to be possible store more node
        if ip < 10:
            uni_id = int("%d0%d" %(idi, ip))
        else:
            uni_id = int("%d%d" %(idi, ip))


        newmessage = Message(uni_id, message, idi)

        self.store.append(newmessage)


# ------------------------------------------------------------------------------------------------------
    # We add a value received from another vessel to the store
    def add_value_to_store(self, m, unique_id):

        # next id
        self.current_key = self.current_key + 1

        # store in the dict
        message = ''.join(m)
        newmessage = Message(unique_id, message, self.current_key)

        self.store.append(newmessage)


# ------------------------------------------------------------------------------------------------------
    # We modify a value received in the store
    def modify_value_in_store(self, uni_id, value):
        # we modify a value in the store if it exists
        wait_action = False

        mes= ''.join(value)

        for i in range (0, len(self.store)):
            if self.store[i].uniqueid == uni_id:
                self.store[i].message = mes
                wait_action = True
                break

        if wait_action == False:
        #the information on vessel is not fully update - we have to wait
        #add this action in a list
            wait_node = Message(uni_id, mes, None)
            wait_node.action = modi_post

            self.wait_list.append(wait_node)



# ------------------------------------------------------------------------------------------------------
    # We delete a value received from the store
    def delete_value_in_store(self, uni_id):
        # we delete a value in the store if it exists
        wait_action = False
        for i in range (0, len(self.store)):
            if self.store[i].uniqueid == uni_id:
                wait_action = True
                self.store.pop(i)
                break


        if wait_action == False:
            wait_node = Message(uni_id, None, None)
            wait_node.action = del_post

            self.wait_list.append(wait_node)


# ------------------------------------------------------------------------------------------------------
    # Contact a specific vessel with a set of variables to transmit to it

    def contact_vessel(self, vessel_ip, path, action, key, value, time1):
        # the Boolean variable we will return
        success = False
        # The variables must be encoded in the URL format, through urllib.urlencode
        post_content = urlencode({'action': action, 'key': key, 'value': value, 'time': time1})
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
    def propagate_value_to_vessels(self, path, action, key, value, time1):
        # We iterate through the vessel list
        for vessel in self.vessels:
            # We should not send it to our own IP, or we would create an infinite loop of updates
            if vessel != ("10.1.0.%s" % self.vessel_id):
                # A good practice would be to try again if the request failed
                # Here, we do it only once
                self.contact_vessel(vessel, path, action, key, value, time1)


# ------------------------------------------------------------------------------------------------------



# ------------------------------------------------------------------------------------------------------
#       BlackboardRequestHandler
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
# ------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------
# Request handling - GET
# ------------------------------------------------------------------------------------------------------
    # This function contains the logic executed when this server receives a GET request
    # This function is called AUTOMATICALLY upon reception and is executed as a thread!
    def do_GET(self):
        print("Receiving a GET on path %s" % self.path)
        # if path is /board, only the boardcontents template should be updated, else the whole page
        if self.path == '/board':
            self.update_board()
        else:
            self.do_GET_Index()


# ------------------------------------------------------------------------------------------------------
# GET logic and update_board - specific path
# ------------------------------------------------------------------------------------------------------

    def update_board(self):
        self.set_HTTP_headers(200)
        new_entry = ""

        for i in range (0, len(self.server.store) ):
        #for every item in store
            idi = self.server.store[i].uniqueid
            entry = entry_template % ("entries/" + str(idi), i, (self.server.store[i].message)) #create entries
            new_entry += entry
        newboard = boardcontents_template #put the new entries into the boardcontents
        newboard = newboard[:-5]
        newboard += '<p>'
        newboard += new_entry
        newboard += '</div>'
        self.wfile.write(newboard)
# ------------------------------------------------------------------------------------------------------

    def do_GET_Index(self):
        # We set the response status code to 200 (OK)
        self.set_HTTP_headers(200)
        # We should do some real HTML here

        html_reponse = board_frontpage_header_template + boardcontents_template + board_frontpage_footer_template
        new_entry = ""

        for i in range (0, len(self.server.store) ):#for each item in store, create entries
            idi = self.server.store[i].uniqueid
            entry = entry_template % ("entries/" + str(idi), i, self.server.store[i].message)
            new_entry += entry
        boardcontents_template2 = boardcontents_template[:-5] #put the new entries into the boardcontents
        boardcontents_template2 += '<p>'
        boardcontents_template2 += new_entry
        boardcontents_template2 += '</div>'
        html_reponse = board_frontpage_header_template + boardcontents_template2 + board_frontpage_footer_template

        self.wfile.write(html_reponse)

# ------------------------------------------------------------------------------------------------------



# ------------------------------------------------------------------------------------------------------
# Request handling - POST
# ------------------------------------------------------------------------------------------------------
    def do_POST(self):
        print("Receiving a POST on %s" % self.path)
        # Here, we should check which path was requested and call the right logic based on it
        # We should also parse the data received
        # and set the headers for the client

        id_mod_del = -1
        post_data = self.parse_POST_request()
        self.set_HTTP_headers(200)
        retransmit = False
        start = None
        list_time = []


        if self.path == "/board":
            # submit - add_post
            if 'action' in post_data:
                # receive a new post from other vessels
                if ''.join(post_data['action']) == add_post:
                    # new value
                    uni_id = int( ''.join(post_data['key']) )
                    start_time = float(''.join(post_data['time']))

                    #if the id is not occupy with other post - there isn't any conflict
                    self.server.add_value_to_store(''.join(post_data['value']), uni_id)
                    end = time()

                    t_reach_cons = end - start_time
                    list_time.append(t_reach_cons)
                    global counter
                    counter+=1

                    if counter == num_messages:
                        print"Time to reach consistency: %f" %(max(list_time))

            else:
                # new post - submit information write by the own vessel
                mutex_list.acquire()
                self.server.add_value_to_store_new(post_data['entry'])
                size = len(self.server.store) - 1
                key = self.server.store[size].uniqueid
                mutex_list.release()

                action = add_post
                retransmit = True

                #starting time for testing lab3
                start = time()


        elif 'delete' in post_data:
            # received a request for modify or delete
            id_mod_del = int(''.join(post_data['delete']))
            key = int(self.path[9:])

            if id_mod_del == 0:
                # modify
                self.server.modify_value_in_store(key, post_data['entry'])
                action = modi_post
                retransmit = True

            elif id_mod_del == 1:
                # delete
                self.server.delete_value_in_store(key)
                action = del_post
                retransmit = True


        elif 'action' in post_data:
            # update information (modify or delete a string) from another vessel
            uni_id = int(''.join(post_data['key']))

            if ''.join(post_data['action']) == modi_post:
                # update value
                self.server.modify_value_in_store(uni_id, post_data['value'])


            elif ''.join(post_data['action']) == del_post:
                # delete value
                self.server.delete_value_in_store(uni_id)



        if retransmit:
            retransmit = False
            # do_POST send the message only when the function finishes
            # We must then create threads if we want to do some heavy computation
            #
            # Random content
            thread = Thread(target=self.server.propagate_value_to_vessels, args=(self.path, action, key, ''.join(post_data['entry']), start ))
            # We kill the process if we kill the server
            thread.daemon = True
            # We start the thread
            thread.start()

# ------------------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------------------
#       Reconciliation function - order the list and guarantees
#that all the vessels have the same infomation
# ------------------------------------------------------------------------------------------------------

def reconciliation(lista, wait_list):

    while 1:
        sleep(1)

        # lock (mutex) - only this thread has access to the critical region (self.server.store)
        mutex.acquire()

        if len(wait_list) > 0:
        #there are some action waiting to be realize
            for  i in range (0, len(lista) ):
                if wait_list[i].action == modi_post:
                #modify
                    self.server.modify_value_in_store(wait_list[i].uniqueid, wait_list[i].message)

                elif wait_list[i].action == del_post:
                #delete
                    self.server.delete_value_in_store(wait_list[i].uniqueid)

        #order the list by the unique id
        lista.sort( key=attrgetter('uniqueid'))

        for idi in range (0, len(lista) ):
            lista[idi].id = idi

        #unlock the mutex
        mutex.release()

# ------------------------------------------------------------------------------------------------------



# ------------------------------------------------------------------------------------------------------
#       Main
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

    global num_messages
    num_messages = 40 * (int(sys.argv[2]) - 1)

    global counter
    counter = 0

    # We launch a server
    server = BlackboardServer(('', PORT_NUMBER), BlackboardRequestHandler, vessel_id, vessel_list)
    print("Starting the server on port %d" % PORT_NUMBER)


    t = Thread(target=reconciliation, args=(server.store, server.wait_list) )
    t.daemon = True
    t.start()


    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
        print("Stopping Server")
# ------------------------------------------------------------------------------------------------------
