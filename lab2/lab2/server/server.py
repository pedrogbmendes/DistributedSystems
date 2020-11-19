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
from threading import Thread # Thread Management
from random import randint	#random number
from time import sleep


# ------------------------------------------------------------------------------------------------------

# Global variables for HTML templates
try:
    board_frontpage_footer_template = open('server/board_frontpage_footer_template.html', 'r').read()
    board_frontpage_header_template = open('server/board_frontpage_header_template.html', 'r').read()
    boardcontents_template = open('server/boardcontents_template.html', 'r').read()
    entry_template = open('server/entry_template.html', 'r').read()
except Exception as e:
    print(e)

# ------------------------------------------------------------------------------------------------------
# Static variables definitions
PORT_NUMBER = 8080

# ------------------------------------------------------------------------------------------------------
#     Protocols of communications - actions                 #       from   ->    to         #
# ------------------------------------------------------------------------------------------------------
                                                            #                               #
#normal vessels contact the leader to add a new entry       #                               #
add_leader = "submit_entry_to_leader"                       #   normal_vessel -> leader     #
                                                            #                               #
#the leader send the value with the id to submit in         #                               #
#normal vessel                                              #                               #
add_vessels = "submit_on_vessels"                           #   leader -> normal_vessel     #
                                                            #                               #
#normal vessels contact the leader to modify a new entry    #                               #
mod_leader = "modify_entry_to_leader"                       #   normal_vessel -> leader     #
                                                            #                               #
#the leader send the new value with the id to modify        #                               #
#in normal vessel                                           #                               #
mod_vessels = "submit_on_vessels"                           #   leader -> normal_vessel     #
                                                            #                               #
#normal vessels contact the leader to delete a new entry    #                               #
del_leader = "delete_entry_to_leader"                       #   normal_vessel -> leader     #
                                                            #                               #
#the leader send the new value with the id to delete        #                               #
#in normal vessel                                           #                               #
del_vessels = "delete_on_vessels"                           #   eader -> normal_vessel      #
                                                            #                               #
#leader election algorithm                                  #                               #
leader_elec = "leader_election"                             #   vessel -> vessel            #
                                                            #                               #
#a node sends a message to the neighbour to warn that       #                               #
#some node died during the leader election                  #                               #
dead_neighbour = "dead_neighbour_in_election"               #   vessel -> vessel            #
                                                            #                               #
#when a vessel detects that the leader might be dead        #                               #
#choose a new leader                                        #                               #
new_leader = "leader_dead_new_election"                     #   vessel -> new_leader        #
                                                            #                               #
# ------------------------------------------------------------------------------------------------------


# ------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------
class BlackboardServer(HTTPServer):
    # ------------------------------------------------------------------------------------------------------
    def __init__(self, server_address, handler, node_id, vessel_list):
        # We call the super init
        HTTPServer.__init__(self, server_address, handler)
        # we create the dictionary of values
        self.store = {}
        # We keep a variable of the next id to insert
        self.current_key = -1
        # our own ID (IP is 10.1.0.ID)
        self.vessel_id = vessel_id
        # The list of other vessels
        self.vessels = vessel_list
        #Leader id
        self.leader_id = -1
        #list with the random number_vessels
        self.list_num_rand = {}
        #neighbour id
        self.neighbour_id = -1
        self.max_id = 0
        #list with the nodes dead and the node that are reachable
        self.list_deads = []
        self.list_node = vessel_list

# ------------------------------------------------------------------------------------------------------
    # We add a value received to the store
    def add_value_to_store_leader(self, value):
        # We add the value to the store
        # next id
        self.current_key = self.current_key + 1
        # store in the dict
        value = ''.join(value)
        self.store[self.current_key] = value

# ------------------------------------------------------------------------------------------------------
    # We add a value received to the store
    def add_value_to_store_normal(self, key, value):
        # We add the value to the store
        # next id
        self.current_key = self.current_key + 1
        # store in the dict
        value = ''.join(value)
        self.store[key] = value

# ------------------------------------------------------------------------------------------------------
    # We modify a value received in the store
    def modify_value_in_store(self, key, value):
        # we modify a value in the store if it exists
        if key in self.store.keys():
            value = ''.join(value)
            self.store[key] = value

# ------------------------------------------------------------------------------------------------------
    # We delete a value received from the store
    def delete_value_in_store(self, key):
        # we delete a value in the store if it exists
        if key in self.store.keys():
            del self.store[key]

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
    # We send a received value from leader to all the other vessels of the system
    def propagate_value_to_vessels(self, path, action, key, value):

        if self.leader_id == self.vessel_id or action == new_leader:
        #if I am the leader
            # We iterate through the vessel list
            for vessel in self.vessels:
                # We should not send it to our own IP, or we would create an infinite loop of updates
                if vessel != ("10.1.0.%s" % self.vessel_id):
                    # A good practice would be to try again if the request failed
                    # Here, we do it only once
                    check_connec = self.contact_vessel(vessel, path, action, key, value)

# ------------------------------------------------------------------------------------------------------
    # We send a received value from a normal vessel to the leader
    def propagate_value_to_leader(self, path, action, key, value):

        if self.leader_id != self.vessel_id:
            vessel = "10.1.0.%s" % self.leader_id
            check_connec = self.contact_vessel(vessel, path, action, key, value)
            if check_connec == False:
                #leader is dead
                self.vessels.remove(vessel)
                if self.leader_id in self.list_num_rand.keys():
                    del self.list_num_rand[self.leader_id]

                #new leader
                self.leader_id = max(self.list_num_rand, key = self.list_num_rand.get)
                action = new_leader
                self.propagate_value_to_vessels(None, action, self.leader_id, self.list_num_rand[self.leader_id])
                print "New Leader was elected (id = %d)" %self.leader_id

# ------------------------------------------------------------------------------------------------------
    # We send a received value to all the neighbour's vessels
    # the graph with all vessels is a ring
    def propagate_value_to_neighbor(self, path, action, key, value):
        # We only send it to the neighbour
        vessel ="10.1.0.%d" % (self.neighbour_id)

        #propagate the id and de random number to the neighbour
        check_connec = self.contact_vessel(vessel, path, action, key, value)
        if check_connec == False:
            if vessel in self.list_node:
                id_dead = self.neighbour_id
                self.list_node.remove(vessel)
                self.list_deads.append(vessel)
                vessel_new ="10.1.0.%d" % self.neighbour_id

                #if the neighbour is dead, discover the new neighbour id
                while vessel_new not in self.list_node:
                    if self.max_id == self.neighbour_id:
                        self.max_id = self.vessel_id
                        self.neighbour_id = 1
                    else:
                        self.neighbour_id += 1

                    #address of the destination vessel
                    vessel_new ="10.1.0.%d" % self.neighbour_id

                #warns the new neighbour that
                action1 = dead_neighbour
                self.contact_vessel(vessel_new, path, action1, id_dead, self.max_id)
                action2 = leader_elec

                for i in self.list_num_rand.keys():
                    if i in self.list_num_rand.keys():
                        self.contact_vessel(vessel_new, path, action2, i, self.list_num_rand[i])


                #send the information about the ids and the random numbers to the new neighbour
                self.propagate_value_to_neighbor(path, action, key, value)


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
# GET logic - specific path
# ------------------------------------------------------------------------------------------------------

    def update_board(self):
        self.set_HTTP_headers(200)
        new_entry = ""
        for i in self.server.store.keys(): #for every item in store
            entry = entry_template % ("entries/" + str(i), i, self.server.store[i]) #create entries
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

        #write the leader id and his random number in the html file
        leader_board = board_frontpage_header_template
        aux = leader_board[-330:]
        leader_board = leader_board[:-330]
        leader_board += '</p>Leader id = %d; Random Number = %d</p>' %(self.server.leader_id, self.server.list_num_rand[self.server.leader_id] )
        leader_board += aux

        html_reponse = leader_board + boardcontents_template + board_frontpage_footer_template
        new_entry = ""

        for i in self.server.store.keys(): #for each item in store, create entries
            entry = entry_template % ("entries/" + str(i), i, self.server.store[i])
            new_entry += entry
        boardcontents_template2 = boardcontents_template[:-5] #put the new entries into the boardcontents
        boardcontents_template2 += '<p>'
        boardcontents_template2 += new_entry
        boardcontents_template2 += '</div>'
        html_reponse = leader_board + boardcontents_template2 + board_frontpage_footer_template

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

        if self.server.vessel_id == self.server.leader_id:
            #leader - act like a leader
            self.act_like_a_leader()

        else:
            #normal vessel
            self.act_like_normal_node()

#------------------------------------------------------------------------------------------------------
# Leader node
    def act_like_a_leader(self):

        id_mod_del = -1
        post_data = self.parse_POST_request()
        self.set_HTTP_headers(200)

        if self.path == "/board":
        # submit - new entry
            if 'action' in post_data:
            # new entry from the other normal vessels
                if ''.join(post_data['action']) == add_leader:
                    self.server.add_value_to_store_leader(''.join(post_data['value']))
                    entry = ''.join(post_data['value'])
            else:
            # submit information write by the own leader vessel
                self.server.add_value_to_store_leader(post_data['entry'])
                entry = ''.join(post_data['entry'])

            key = self.server.current_key
            action = add_vessels


        elif 'delete' in post_data:
        # modify or delete in the leader
            id_mod_del = int(''.join(post_data['delete']))
            key = int(self.path[9:])

            if id_mod_del == 0:
                # modify
                self.server.modify_value_in_store(key, post_data['entry'])
                entry = ''.join(post_data['entry'])
                action = mod_vessels

            elif id_mod_del == 1:
                # delete
                self.server.delete_value_in_store(key)
                entry = None
                action = del_vessels


        elif 'action' in post_data:
        # update information (modify or delete a string) from a normal vessel
            key = int(''.join(post_data['key']))

            if ''.join(post_data['action']) == mod_leader:
            # update value
                action = mod_vessels
                entry = ''.join(post_data['value'])
                self.server.modify_value_in_store(key, post_data['value'])

            elif ''.join(post_data['action']) == del_leader:
            # delete value
                action = del_vessels
                entry = None
                self.server.delete_value_in_store(key)

        #we want to retransmit to all the all non-leader (normal) vessels all the tasks done in the leader
        thread = Thread(target=self.server.propagate_value_to_vessels, args=(self.path, action, key, entry))
        #We kill the process if we kill the server
        thread.daemon = True
        # We start the thread
        thread.start()


# ------------------------------------------------------------------------------------------------------
# Normal node
    def act_like_normal_node (self):

        id_mod_del = -1
        retransmit_to_leader = False

        post_data = self.parse_POST_request()
        self.set_HTTP_headers(200)


        if self.path == "/board":
            if 'action' in post_data:
            # received new entry from the leader to post
                if ''.join(post_data['action']) == add_vessels:
                    # new value
                    key = int(''.join(post_data['key']))
                    self.server.add_value_to_store_normal(key, ''.join(post_data['value']))

            else:
            #contact the leader to a new entry
                action = add_leader
                entry = ''.join(post_data['entry'])
                key = None
                retransmit_to_leader = True

        elif 'delete' in post_data:
            # contact the leader to update information (modify or delete)
            id_mod_del = int(''.join(post_data['delete']))
            key = int(self.path[9:])

            if id_mod_del == 0:
            # modify
                action = mod_leader
                entry = ''.join(post_data['entry'])

            elif id_mod_del == 1:
                # delete
                action = del_leader
                entry = None

            retransmit_to_leader = True

        elif 'action' in post_data:
            # update information (modify or delete a string) from the leader
            key = int(''.join(post_data['key']))

            if ''.join(post_data['action']) == mod_vessels:
                # update value
                self.server.modify_value_in_store(key, post_data['value'])

            elif ''.join(post_data['action']) == del_vessels:
                # delete value
                self.server.delete_value_in_store(key)

            elif ''.join(post_data['action']) == dead_neighbour:
                #some is reporting that one vessel died during the leader election
                id_dead = key
                self.max_id = int(''.join(post_data['value']) )

                vessel_dead = "10.1.0.%d" % (id_dead)
                if vessel_dead in self.server.list_node:
                    self.server.list_node.remove(vessel_dead)
                    self.server.list_deads.append(vessel_dead)

                    action = dead_neighbour
                    t_send_dead = Thread(target=self.server.propagate_value_to_neighbor, args=( None, action, id_dead, self.max_id))
                    t_send_dead.daemon = True
                    t_send_dead.start()


            elif ''.join(post_data['action']) == leader_elec:
                #random number of my neighbour
                num_rec = int( ''.join( post_data['value']) )
                id_rec = key

                if id_rec not in self.server.list_num_rand.keys():
                    action = leader_elec
                    self.server.list_num_rand[id_rec] = num_rec
                    if self.server.vessel_id != id_rec:
                        t_send = Thread(target=self.server.propagate_value_to_neighbor, args=( None, action, id_rec, num_rec))
                        t_send.daemon = True
                        t_send.start()

                num_nodes_begin = len(self.server.list_node) + len(self.server.list_deads)
                if  num_nodes_begin == len(self.server.list_num_rand):
                    if self.server.leader_id == -1:
                        self.server.leader_id = 0
                        thread = Thread(target=self.select_leader)
                        thread.daemon = True
                        thread.start()


            elif ''.join(post_data['action']) == new_leader:
                #leader is dead
                vessel = "10.1.0.%s" % self.server.leader_id
                self.server.vessels.remove(vessel)
                if self.server.leader_id in self.server.list_num_rand.keys():
                    del self.server.list_num_rand[self.server.leader_id]

                self.server.leader_id = key
                print "New Leader was elected (id = %d)" %self.server.leader_id



        if retransmit_to_leader:
            retransmit_to_leader = False

            thread = Thread(target=self.server.propagate_value_to_leader, args=(self.path, action, key, ''.join(post_data['entry'])))
            thread.daemon = True
            thread.start()

# ------------------------------------------------------------------------------------------------------
    def select_leader(self):
        #wainting to finish to receive all the communications
        sleep(15)

        for addr_dead in self.server.list_deads:
            if addr_dead[-2] == '.' :
                id_dead = int(addr_dead[-1])
            else:
                id_dead = int(addr_dead[-2:])

            if id_dead in self.server.list_num_rand.keys():
                del self.server.list_num_rand[id_dead]

        self.server.leader_id = max(self.server.list_num_rand, key = self.server.list_num_rand.get)
        print "Leader was elected (id = %d)" %self.server.leader_id



# ------------------------------------------------------------------------------------------------------

# ------------------------------------------------------------------------------------------------------
#Leader election algorithm - we choose the leader
def leader_election(server, my_id):

    num_rand = randint(0, PORT_NUMBER)
    action = leader_elec
    #wait for the initialization of all vessels
    sleep(1)

    if len(server.vessels) == (server.vessel_id):
    #node with the highest id - his neighbour is the node id = 1
        server.neighbour_id = 1
    else:
    #all the other nodes
        server.neighbour_id = server.vessel_id + 1

    server.list_num_rand[vessel_id] = num_rand

    t_send = Thread(target=server.propagate_value_to_neighbor, args=( None, action, my_id, num_rand))
    t_send.daemon = True
    t_send.start()


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

    server.max_id = int(sys.argv[2])
    leader_election(server, vessel_id)

    try:
        server.serve_forever()

    except KeyboardInterrupt:
        server.server_close()
        print("Stopping Server")
# ------------------------------------------------------------------------------------------------------
