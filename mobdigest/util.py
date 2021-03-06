# general utilities

from google.appengine.api import mail
from datetime import date, timedelta, datetime
from mailmsg import mailmsg
from untangle import untangle, original_text
from collections import Counter
# from words import stopwords
import re

import logging
import re

def remove_linebreaks(my_string):
    new_string = my_string.replace('\n', '').replace('\r', '').replace('\t', '').strip()
    return new_string


def getStats(days):
    some_days_ago = date.today() - timedelta(days=days)
    q = mailmsg.gql("WHERE add_date > :1 ", some_days_ago)
    results = q.fetch(limit=10000)
    total_messages = len(results)
    ot_messages = 0
    new_threads = 0
    proper_disposal = 0
    wtf = 0
    plus_one = 0
    unsbu = 0
    shortest = 1000
    longest = 0
    total_len = 0
    
    # re for pottymouth score: 
    badwords = 'fuck|shit|piss|damn|dick|cunt'
    
   
    # dict of original msg ID: [int count of replies, subject] to find longest
    threads = {}
    
    # dict of message ID : [# of replies, subject + first 80 char] to find most-replied-to msgs
    # not implemented yet:
    # replies = {}
    
    # dict of poster email: [# of messages, pottymouth score, untrimmed messages]
    posters = {}
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
    
    # start counting stuff - this is kinda gross, maybe there's a more efficient way?:
    
    for msg in results:
        # ignore all mobstats
        if '[MoBStats]' in msg.subject:
            continue
        
        # first, process body to only get original content
        processed_text = untangle(msg.body)       
        
        
        msg_body = " ".join(original_text(processed_text, 'ORIG'))
        
        # print u'body = ' , msg_body.encode('ascii','ignore')
        
        if msg_body is None:
            continue
        
        # get word frequencies:
        '''
        pattern = re.compile(r'[^\w\s.]')
        msg_content = re.sub(pattern,'', msg_body)
        msgwords = set( msg_content.lower().split())
        words = msgwords.difference(stopwords)    
        for word in words:
            if len(word)>3 and len(word)<15:
                word_freq[word]+=1
                '''

        in_group_buy = 0
        
        # count sender
        if msg.sender in posters:
            posters[msg.sender][0] += 1 
        else:
            posters[msg.sender] = [1, 0, 0]
    
        # calc pottymouth score:
        potty = re.findall(badwords, msg_body, re.I)
        if len(potty) > 0:
            posters[msg.sender][1] += len(potty)
            
        # look for group buys:
        if any(k in msg.subject[0:40].lower() for k in ['group buy', 'bulk buy']):
            in_group_buy = 1
            if not msg.subject.lower().startswith('re:') and msg.subject not in group_buys :
                group_buys[msg.subject] = []               
                
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
        weekday = msg.add_date.strftime('%a')
        day_freq[weekday] += 1
        
        # hack: UTC-5:00 for EST:
        time_hour = int(msg.add_date.strftime('%H')) - 5
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
        if any(w in msg.subject[:15].lower() for w in ot_words): 
            ot_messages += 1 
            
        # new threads have no "in reply to"
        if msg.in_reply_to == None:
            new_threads += 1   
            threads[msg.message_id] = [1, msg.subject]
            
        else:
            # see what thread we refer to:
            for ref in msg.references:
                if threads.has_key(ref):
                    threads[ref][0] += 1
                    
        # look for new sigs
        # NOTE: tried using untangle, doesn't seem to currently work
            
        sigs = re.findall(r'_{40}\s+(.*?)\s+Brewers\s+mailing\s+list', msg.body, re.DOTALL)      
        for sig in sigs:            
            if sig not in new_sigs and len(sig) < 250 and ">" not in sig:
                new_sigs.append(sig)
        # if there are more than one sig, we have an untrimmed message
        if len(sigs) > 1:
            posters[msg.sender][2] += 1
                
        # look for new subs:
        # format: blurb@gmail.com has been successfully subscribed to Brewers. 
        if 'subscription notification' in msg.subject and not msg.subject.lower().startswith('re'):
            sub_email_obj = re.search(r'(\w+@[^\s]*) has\s*been\s*successfully\s*subscribed', msg_body)
            if sub_email_obj:
                new_subs.append(sub_email_obj.group(1))
                
        if 'unsubscribe notification' in msg.subject and not msg.subject.lower().startswith('re'):
            unsub_email_obj = re.search(r'(\w+@[^\s]*) has been removed from Brewers.', msg_body)
            if unsub_email_obj:
                unsubs.append(unsub_email_obj.group(1))
         
        
           
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

    return stats
            

def sendStats(email_address, stats, send_it=False):

    body = "Dear {0}, here are some stats from the last 7 days of MoB postings.\n\n".format(email_address)

    body = body + stats
    body += "\n\n----------------------------\n"
    body += "Message generated on {0} by the MoB Digest stats generator run by drew.avis@gmail.com\n".format(datetime.now() - timedelta(hours=5))
    message = mail.EmailMessage(sender="MobDigest <drew.avis@gmail.com>",
              to=email_address,
              subject="[MoBStats] MoB Digest Stats",
              body=body)
    logging.info("sending email to: " + email_address)  
    
    if send_it:
        message.send()
    return body

def makeGraph(keys_array, data_dict):
    # take a dict of values, and create an ascii graph, using the sorted keys array
    # TODO: add y-axis
    # find max value to scale to 10:
    mx = max(data_dict.values())
    incr = 1
    if mx > 10:
        incr = mx / 10    
    graph = []    
    
    for i in reversed(range(10)):
        line = []
        for k in keys_array:
            if data_dict[k] > i * incr:
                line.append('*')
            else:
                line.append(' ')
        graph.append(line)
        
    return graph
    
