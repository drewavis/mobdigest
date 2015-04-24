from google.appengine.ext import db

# message class
class mailmsg(db.Model):
    subject = db.StringProperty()
    sender = db.StringProperty()
    sender_email = db.StringProperty()
    to = db.StringProperty()
    add_date = db.DateTimeProperty(auto_now_add=True)
    email_date = db.StringProperty()
    body = db.TextProperty()
    
    # gmail threading props
    message_id = db.StringProperty() 
    in_reply_to = db.StringProperty()
    references = db.StringListProperty()
    
    original = db.TextProperty()
    
