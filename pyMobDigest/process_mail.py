#!/usr/bin/python

import httplib2
import base64
import email
import re

from apiclient.discovery import build
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import run

from datetime import date, timedelta, datetime
from collections import Counter

from email.utils import parsedate_tz, mktime_tz
from time import mktime

def main():
  # re for pottymouth score: 
  badwords = 'fuck|shit|piss|damn|dick|cunt'
  # Path to the client_secret.json file downloaded from the Developer Console
  CLIENT_SECRET_FILE = 'client_secret.json'


  # Check https://developers.google.com/gmail/api/auth/scopes for all available scopes
  OAUTH_SCOPE = 'https://www.googleapis.com/auth/gmail.readonly'

  # Location of the credentials storage file
  STORAGE = Storage('gmail.storage')

  # Start the OAuth flow to retrieve credentials
  flow = flow_from_clientsecrets(CLIENT_SECRET_FILE, scope=OAUTH_SCOPE)
  http = httplib2.Http()

  # Try to retrieve credentials from storage or run the flow to generate them
  credentials = STORAGE.get()
  if credentials is None or credentials.invalid:
    credentials = run(flow, STORAGE, http=http)

  # Authorize the httplib2.Http object with our credentials
  http = credentials.authorize(http)

  # Build the Gmail service from discovery
  gmail_service = build('gmail', 'v1', http=http)

  # Some global counters
  ot_messages = 0
  new_threads = 0
  proper_disposal = 0
  wtf = 0
  plus_one = 0
  unsbu = 0
  shortest = 1000
  longest = 0
  total_len = 0

  # set up dicts for processing:
  # dict of poster email: [# of messages, pottymouth score, untrimmed messages]
  posters = {}
  # dict of original msg ID: [int count of replies, subject] to find longest
  threads = {}
  # links - a dict of 'type' : [array of urls]
  links = {}
    
  # group buys - a dict of msg id : [subject, array of links in thread]
  group_buys = {}
  
  # subs:
  new_subs = []
  unsubs = []
  
  # sigs:
  new_sigs = []    

  # date & time frequencies
  day_freq = Counter()
  time_freq = Counter()
  
  # word frequencies
  # word_freq = Counter()

  # get some messages
  some_days_ago = date.today() - timedelta(days=7)
  qry = some_days_ago.strftime("after:%y/%m/%d")

  msgs = gmail_service.users().messages().list(userId='me',labelIds='Label_7',q=qry,  maxResults=2).execute()

  if msgs['messages']:
    print '# messages: ', len(msgs['messages'])
    for m in msgs['messages']:
      msg = GetMimeMessage(gmail_service,'me',m['id'])

      print msg.keys()


      for s in ['Subject', 'Sender', 'From', 'Date']:
        print "%s: %s" % (s, msg[s])

      # ignore all mobstats
      if '[MoBStats]' in msg['Subject']:
          continue

      msg_body = msg.get_payload()
      # skip empty:
      if msg_body is None:
            continue

      in_group_buy = 0

      # count sender
      if msg['From'] in posters:
          posters[msg['From']][0] += 1 
      else:
          posters[msg['From']] = [1, 0, 0]

      # calc pottymouth score:
      potty = re.findall(badwords, msg_body, re.I)
      if len(potty) > 0:
          posters[msg['From']][1] += len(potty)

      # find offers for various phrases:
      disposals = re.findall(r'(proper disposal)', msg_body, re.I)
      proper_disposal += len(disposals)
      wtfs = re.findall(r'(wtf)', msg_body, re.I)
      wtf += len(wtfs)
      plus_ones = re.findall(r'(\+1)', msg_body, re.I)        
      plus_one += len(plus_ones)
      unsbus = re.findall(r'(unsbu)', msg_body, re.I)
      unsbu += len (unsbus)

      # message lengths
      msg_word_count = len(msg_body.split())
      if msg_word_count > longest:
          longest = msg_word_count
      if msg_word_count < shortest:
          shortest = msg_word_count
      total_len += msg_word_count
      
      # figure out date and time for frequencies:   
      tt = parsedate_tz(msg['Date'])
      dt = datetime.fromtimestamp(mktime_tz(tt))

      weekday = dt.strftime('%a')
     
      day_freq[weekday] += 1
      
      # hack: UTC-5:00 for EST:
      time_hour = int(dt.strftime('%H')) - 5
      if time_hour < 0:
          time_hour += 24
      time_freq[time_hour] += 1

      # look for links:    
      msg_links = re.findall(r'(https?://[^\s^>]+)', msg_body)
      for link in msg_links:
          if 'lists.barleyment.ca' in link or len(link) > 60:
              continue
          link_type = 'other'  
          if any(k in link for k in ['beer', 'brew']):
              link_type = 'Brewing' 
          # scan for now, but we don't need this for the output, there are too many links as is     
          elif 'imgur.' in link:
              link_type = 'Imgur'
          elif 'amazon.' in link:
              link_type = 'Amazon'
          elif 'ebay.' in link:
              link_type = 'Ebay'
          elif 'docs.google' in link:
              link_type = 'Google Docs'
          elif 'youtube' in link:
              link_type = 'Youtube'            
              
          # save the link in the group_buys array if this is a group buy
          if in_group_buy == 1:       
              # using subjects is ugly and possibly inaccurate
              # this should be re-visited to use message_id instead             
              subj = msg.subject
              if subj.lower().startswith('re:'):
                  subj = subj[4:]
              if subj not in group_buys:
                  group_buys[subj] = [link]
              else:
                  if link not in group_buys[subj]:
                      group_buys[subj].append(link)
              
          # add it
          elif link_type not in links:
              links[link_type] = [link]
          elif link not in links[link_type]:
              links[link_type].append(link)      
         
      
      # look for ot - subjects probably always start with Re: [MoB] or just [MoB] (first msg in thread)
      ot_words = ['ot:', '[ot]', 'ot ']
      if any(w in msg['Subject'][:15].lower() for w in ot_words): 
          ot_messages += 1 
          
      # new threads have no "in reply to"
      thread_id = m['threadId']
      if not threads.has_key(thread_id) :
          new_threads += 1   
          threads[thread_id] = [1, msg['Subject']]
          
      else:
           threads[thread_id][0] += 1
                  
      # look for new sigs
      # NOTE: tried using untangle, doesn't seem to currently work
          
      sigs = re.findall(r'_{40}\s+(.*?)\s+Brewers\s+mailing\s+list', msg_body, re.DOTALL)      
      for sig in sigs:            
          if sig not in new_sigs and len(sig) < 250 and ">" not in sig:
              new_sigs.append(sig)
      # if there are more than one sig, we have an untrimmed message
      if len(sigs) > 1:
          posters[msg['From']][2] += 1
              
      # look for new subs:
      # format: blurb@gmail.com has been successfully subscribed to Brewers. 
      if 'subscription notification' in msg['Subject'] and not msg['Subject'].lower().startswith('re'):
          sub_email_obj = re.search(r'(\w+@[^\s]*) has\s*been\s*successfully\s*subscribed', msg_body)
          if sub_email_obj:
              new_subs.append(sub_email_obj.group(1))
              
      if 'unsubscribe notification' in msg['Subject'] and not msg['Subject'].lower().startswith('re'):
          unsub_email_obj = re.search(r'(\w+@[^\s]*) has been removed from Brewers.', msg_body)
          if unsub_email_obj:
              unsubs.append(unsub_email_obj.group(1))

    # end for each msg

    # create stats:
    # generate stats message
    stats = "Stats for timespan {0} to {1}\n".format(some_days_ago, date.today())
    stats += "Total messages: {0}\n".format(total_messages)
    stats += "Marked OT messages: {0} ({1:.0f}%)\n".format(ot_messages, (float(ot_messages) / float(total_messages) * 100))
    stats += "New threads: {0}\n".format(new_threads)
    stats += "Longest message (words): {0}\n".format(longest)
    stats += "Shortest message (words): {0}\n".format(shortest)
    stats += "Average message length (words): {0:.0f}\n".format(total_len / total_messages) 
    stats += "Offers of 'proper disposal': {0}\n".format(proper_disposal)  
    stats += "WTFs: {0}\n".format(wtf)       
    stats += "+1's: {0}\n".format(plus_one)     
    stats += "unsbus: {0}\n".format(unsbu)  

    
    if len(new_subs) > 0:
        stats += "New Subs:\n"
        for sub in new_subs:
            stats += "  {0}\n".format(sub)
    else:
        stats += "No new subs.\n"
        
    if len(unsubs) > 0:
        stats += "Unsubscriptions:\n"
        for sub in unsubs:
            stats += "  {0}\n".format(sub)
    else:
        stats += "No unsubscriptions.\n"
    
    if len(group_buys) > 0:
        stats += "Group buy threads:\n"
        for g in group_buys:
            stats += "  {0}\n".format(g)
            if len(group_buys[g]) > 0:
                stats += "   - Thread links:\n".format(g)
                for l in group_buys[g]:
                    stats += "    {0}\n".format(l)
                    
    stats += "Number of unique posters: {0}\n".format(len(posters))        
    sorted_posters = sorted(posters, key=lambda key: posters[key][0], reverse=True)    
    stats += "\nTop 10 posters (untrimmed):\n"
    for item in sorted_posters[:10]:
        stats += "{0} : {1} ({2})\n".format(item, posters[item][0], posters[item][2])
    
    potty_posters = sorted(posters, key=lambda key: posters[key][1], reverse=True)
    stats += "\n[Drumroll...] And the Horshaq Memorial @#$! Awards for the week go to:\n"
    for item in potty_posters[:3]:
        stats += "{0} : {1}\n".format(item, posters[item][1])
    
    untrimmed_posters = sorted(posters, key=lambda key: (float(posters[key][2])/float(posters[key][0])), reverse=True)
    stats += "\n[Drumroll...] And the MacKay Memorial Don't Be A Dickhead Awards go to:\n"
    for item in untrimmed_posters[:10]:
        stats += "{0} : {1}%\n".format(item, float(posters[item][2])/float(posters[item][0])*100)
        
    sorted_threads = sorted(threads, key=lambda key: threads[key][0], reverse=True)
    stats += "\nTop 10 longest (new) threads:\n"
    for item in sorted_threads[:10]:
        stats += "{0} : {1}\n".format(threads[item][1], threads[item][0])
        
    
    '''
    Not really working: 
    stats += "\nCrickets and tumbleweeds (bottom 10):\n"
    for item in sorted_threads[-10:]:
        stats += "{0} : {1}\n".format(threads[item][1], threads[item][0])       
    '''
     
    '''
    sorted_words = sorted(word_freq,key=lambda key: word_freq[key], reverse=True)
    stats += "\nTop 10 trending words:\n"
    for w in sorted_words[:10]:
        stats += "{0} : {1}\n".format(w, word_freq[w])
    '''     
     
    stats += "\nPosting frequency by hour:\n"
    hr_graph = makeGraph(range(24), time_freq)

    
    for l in hr_graph:
        for p in l:
            stats += " {0} ".format(p)
        stats += "\n"
    for hr in range(24):
        stats += "{0:2}|".format(hr)
    stats += "\n"
    for hr in range(24):
        stats += "{0:2}|".format(time_freq[hr])
        
    stats += "\n\nPosting frequency by day:\n"
    wk_days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    wk_graph = makeGraph(wk_days, day_freq)
    
    # Weekday frequency    
    #graph:
    for l in wk_graph:
        for p in l:
            stats += " {0}  ".format(p)
        stats += "\n"
    # x-axis:
    for d in wk_days:
        stats += "{0:3}|".format(d)
    stats += "\n"
    for wk in wk_days:
        stats += "{0:3}|".format(day_freq[wk])
    
    '''
    stats += "\n\nNew sigs:\n"  
    for sig in new_sigs:
        stats += "{0}\n".format(sig) 
    '''    
    stats += "\n\nBrewing-related links found:\n"    
    if 'Brewing' in links:
        sorted_links = sorted(links['Brewing'])
        for item in sorted_links:
            stats += "  {0}\n".format(item)
    print stats
   
# straight from the Google docs:
def GetMimeMessage(service, user_id, msg_id):
  """Get a Message and use it to create a MIME Message.

  Args:
    service: Authorized Gmail API service instance.
    user_id: User's email address. The special value "me"
    can be used to indicate the authenticated user.
    msg_id: The ID of the Message required.

  Returns:
    A MIME Message, consisting of data from Message.
  """
  try:
    message = service.users().messages().get(userId=user_id, id=msg_id,
                                             format='raw').execute()

    # print 'Message snippet: %s' % message['snippet']

    msg_str = base64.urlsafe_b64decode(message['raw'].encode('ASCII'))

    mime_msg = email.message_from_string(msg_str)

    return mime_msg
  except errors.HttpError, error:
    print 'An error occurred: %s' % error

main()