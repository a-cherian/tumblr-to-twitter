import credentials

import os
import tweepy
import pytumblr2
import requests
import calendar
from datetime import datetime, timezone

auth = None
twitter_api = None
twitter_client = None
tumblr_client = None

def initializeTwitter():
    global auth
    global twitter_client
    global twitter_api
    auth = tweepy.OAuthHandler(credentials.twt_API_key, credentials.twt_API_secret_key)
    auth.set_access_token(credentials.twt_access_token, credentials.twt_access_token_secret)
    twitter_api = tweepy.API(auth)
    twitter_client = tweepy.Client(
        consumer_key=credentials.twt_API_key,
        consumer_secret=credentials.twt_API_secret_key,
        access_token=credentials.twt_access_token,
        access_token_secret=credentials.twt_access_token_secret
    )

def initializeTumblr():
    global tumblr_client
    tumblr_client = pytumblr2.TumblrRestClient(
      credentials.tum_consumer_key,
      credentials.tum_API_secret_key,
      credentials.tum_access_token,
      credentials.tum_access_token_secret
    )

def getNewPosts(blog, lastCheck):
    posts = tumblr_client.posts(blog, type="photo", reblog_info="true", npf="true")
    new_posts = [post for post in posts["posts"] if
                (post["timestamp"] > int(lastCheck) and
                    "reblogged_root_id" not in post.keys())]
    return new_posts

def checkLastUpdate():
    if "photos" in os.getcwd():
        os.chdir("..")
    f = open('last_update.txt','a+')
    f.seek(0);
    time = f.read()
    f.close()
    try:
        return int(time)
    except ValueError:
        return 0

def changeLastUpdate(time):
    if "photos" in os.getcwd():
        os.chdir("..")
    f = open('last_update.txt','w')
    f.write(str(time))
    f.close()

def uploadImage(tag, post, media_num):
    large_dimensions = False
    media_id = ""
    alt_text = ""
    content = post["content"][media_num]
    if content["type"] == "text":
        return [post, large_dimensions, ""]
    character = post["summary"][:post["summary"].index(" transparent")]
    if tag in post["tags"]:
        if tag == "b&w":
            alt_text = "a transparent, black & white manga panel of " + character + " from jojo."
        elif tag == "colored":
            alt_text = "a transparent, colored manga panel of " + character + " from jojo."
        else:
            alt_text = "a transparent manga panel of " + character + " from jojo."
        post["content"][media_num]["alt_text"] = alt_text

        i = 0
        img = content["media"][i]
        while i < len(content["media"]) and (img["height"] > 900 or img["width"] > 900):
            img = content["media"][i]
            i += 1
        url = img["url"]

        if i > 0:
            large_dimensions = True

        filename = str(post["id"]) + '_' + tag + '.png'
        request = requests.get(url, stream=True)
        if request.status_code == 200:
            with open(filename, 'wb') as image:
                for chunk in request:
                    image.write(chunk)

        media = twitter_api.media_upload(filename=filename)
        media_id = media.media_id_string
        twitter_api.create_media_metadata(media_id, alt_text)

    return [post, large_dimensions, media_id]

def processPost(post):
    photos = []
    if "photos" not in os.getcwd():
        os.chdir("photos")
    large_dimensions = False
    media_num = 0

    tags = ["b&w", "colored", "two", "three", "four"]

    for tag in tags:
        post, ld, newPhoto = uploadImage(tag, post, media_num)
        if newPhoto != "":
            photos.append(newPhoto)
            media_num += 1
        large_dimensions = large_dimensions or ld

    return [post, photos, large_dimensions]

def postTweet(caption, photos, large_dimensions, post_url):
    tweet = twitter_client.create_tweet(text=caption, media_ids=photos)

    if large_dimensions:
        twitter_client.create_tweet(text='this image has been resized to maintain transparency on twitter. for the full resolution image, go here: ' + post_url, in_reply_to_tweet_id=tweet.data["id"])

    return tweet

def main():
    initializeTwitter()
    initializeTumblr()

    if "photos" not in os.listdir():
        os.mkdir("photos")

    print("Last updated: " + str(datetime.fromtimestamp(checkLastUpdate())))
    posts = getNewPosts(credentials.blogUrl, checkLastUpdate())
    print(str(len(posts)) + " new posts found")

    for post in posts:
        post, photos, large_dimensions = processPost(post)
        print("Attempting to tweet \"" + post["summary"] + "\"...")
        print("Response: " + str(postTweet(post["summary"], photos, large_dimensions, post["post_url"])))

    if len(posts) > 0:
        d = datetime.now(timezone.utc)
        unixtime = calendar.timegm(d.utctimetuple())
        changeLastUpdate(unixtime)

if __name__ == '__main__':
    main()
