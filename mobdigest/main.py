import webapp2
import logging
import re
from google.appengine.ext.webapp.mail_handlers import InboundMailHandler
from google.appengine.ext import db
from google.appengine.api import users
import util

from mailmsg import mailmsg

class LogSenderHandler(InboundMailHandler):
    # must implement this method to handle incoming emails
    # message.original is a native python messaging.email object
    # we can use references to re-create threads
    def receive(self, message):
        logging.info("Received a message from: " + message.sender)
        email = message.original               
        m = mailmsg()
        #m.body = get_body(email)
        m.body = get_body2(message)
        m.sender = util.remove_linebreaks(email['From'])   
        e = re.search('<(.*?@.*?)>', m.sender)
        if e:
            m.sender_email=e.group(1)
        m.to = util.remove_linebreaks(email['To'])
        if email['CC'] != None:
            m.cc = util.remove_linebreaks(email['CC'])
        m.email_date = email['Date']
        m.subject = util.remove_linebreaks(email['Subject'])        
        
        m.in_reply_to = email['In-Reply-To']
        m.message_id = email['Message-ID']
        refs = email['References']
        if (refs != '' and refs != None):
            m.references = refs.split()  
          
        # don't need unless you're debugging:          
        # m.original = message.original.as_string()
        
        # store new message:
        m.put()  
 

class MainPage(webapp2.RequestHandler):      
    def get(self):
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write('Hello, Barleyment Digest!')
 
# only use to do an admin wipe of all data, shouldn't need this too often:        
class DelAll(webapp2.RequestHandler):      
    def get(self):        
        self.response.headers['Content-Type'] = 'text/plain'
        
        resp = 'Hello, Barleyment Digest!'
        
        if users.is_current_user_admin():
            query = mailmsg.all(keys_only=True)
            msgs =query.fetch(1000)
            db.delete(msgs) 
            resp='Deleted a bunch'
            
        self.response.out.write(resp)        

class ReportStats(webapp2.RequestHandler):      
    def get(self):
        stats = util.getStats(7)
        # actually sends out the report:
        util.sendStats('brewers@lists.barleyment.ca', stats, True)
        
      
class StatsHandler(webapp2.RequestHandler):      
    def get(self):
        greeting = "LOL"
        user = users.get_current_user()
        
        if user:
            greeting = ("Welcome, %s! (<a href=\"%s\">sign out</a>)\n" %
                        (user.nickname(), users.create_logout_url("/")))
            if users.is_current_user_admin():
                greeting += "stats not sent to %s\n" % user.email()
                # just get 1 day of stats for testing:
                stats = util.getStats(1)
                greeting += util.sendStats(user.email(), stats, True)               
               
                
        else:
            greeting = ("<a href=\"%s\">Sign in or register</a>." %
                        users.create_login_url("/"))

        self.response.out.write("<html><body><pre>%s</pre></body></html>" % greeting)

# from SO thread: http://stackoverflow.com/questions/594545/email-body-is-a-string-sometimes-and-a-list-sometimes-why
def get_body(msg):
    
    maintype = msg.get_content_maintype()
    if maintype == 'multipart':
        for part in msg.get_payload():
            if part.get_content_maintype() == 'text':
                return part.get_payload()
    elif maintype == 'text':
        return msg.get_payload()
    
def get_body2(msg):
    plaintext_bodies = msg.bodies('text/plain')    
    txt = ''
    for content_type, body in plaintext_bodies:  
        txt = body.decode()  
        break
    return txt
        
    
    

# run application:
application = webapp2.WSGIApplication([('/', MainPage),
                                       ('/stats',StatsHandler),
                                       ('/delall',DelAll),
                                       ('/report/stats', ReportStats),
                                    LogSenderHandler.mapping()
                                    ],
                                      debug=True)


