from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from bs4 import BeautifulSoup
import urllib
import time
import json
import re
import os
import argparse

# Put your email and password in these variables, make sure to have the quotation marks around them
# This is a dummy account, you may change it to yours if you want
YOUR_EMAIL_ADDRESS = "bbudihaha@gmail.com"
YOUR_PASSWORD = "budihaha12345"

# Base URL
BASE_URL = 'https://www.quora.com'

# File paths
PROJECT_ROOT = os.path.dirname(os.path.realpath(__file__))
USER_OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'result_users.json')
ANSWER_OUTPUT_FILE = os.path.join(PROJECT_ROOT, 'result_answers.json')
FINAL_FILE = os.path.join(PROJECT_ROOT, 'final_users.json')

list_of_writers = []
following_list = []


def login(driver):
    '''
    - Input: webdriver
    - desc: login to quora
    - Output: void
    '''
    print("Logging in to Quora...")
    wait = WebDriverWait(driver, 30)
    # Find sign-in by Google button and click it
    elem = driver.find_element_by_class_name("google_button")
    elem.click()
    time.sleep(8)
    window_before = driver.window_handles[0]
    window_after = driver.window_handles[1]

    # Switch to login popup
    time.sleep(2)
    driver.switch_to_window(window_after)
    # Enter Email address and submit
    emailInput = driver.find_element_by_xpath("//input[@id='Email']")
    print('Entering email...')
    emailInput.send_keys(YOUR_EMAIL_ADDRESS)
    driver.find_element_by_class_name("rc-button-submit").click()
    time.sleep(4)

    wait.until(EC.presence_of_element_located((By.ID, "Passwd")))

    # Enter Password and submit
    pwInput = driver.find_element_by_xpath("//input[@id='Passwd']")
    print('Entering password...')
    try:
        pwInput.send_keys(YOUR_PASSWORD)
    except:
        print("FAIL")
    time.sleep(4)
    pwSubmit = driver.find_element_by_id("signIn").click()
    time.sleep(5)

    # need to switch to first window again
    driver.switch_to_window(window_before)


def process_answer_divs(current_html, url, question_text, a):
    answer_retrieved = False
    answers_html = current_html.get_attribute("innerHTML").encode("utf-8")
    answers_soup = BeautifulSoup(answers_html, 'html.parser')
    answer_divs = answers_soup.find_all('div', class_='Answer')
    for answer_div in answer_divs:
        answer_author_object = answer_div.find('a', class_='user')
        if answer_author_object is None:
            continue
        answer_author_link = 'https://www.quora.com' + answer_author_object['href']
        if answer_author_link == url:
            answer_author = answer_div.find('a', class_='user')
            answer_author = answer_author_object.get_text()
            the_answer = answer_div.find('span', class_='rendered_qtext').get_text()
            try:
                answer_views = answer_div.find('span', class_='meta_num').get_text()
                if 'k' in answer_views:
                    answer_views = re.sub(r'\D', '', answer_views)
                    answer_views = float(answer_views) * 1000
                else:
                    answer_views = re.sub(r'\D', '', answer_views)
                answer_views = int(answer_views)
            except:
                answer_views = 0
            try:
                # Get the number of upvotes of each answer
                answer_upvotes = answer_div.find('span', class_='count').get_text()
                if 'k' in answer_upvotes:
                    # answer_upvotes = answer_upvotes[0:len(answer_upvotes) - 1]
                    answer_upvotes = re.sub(r'\D', '', answer_upvotes)
                    answer_upvotes = float(answer_upvotes) * 1000
                else:
                    answer_upvotes = re.sub(r'\D', '', answer_upvotes)
            except:
                answer_upvotes = 0
            answer_upvotes = int(answer_upvotes)
            new_data = {
                "answer": the_answer,
                "author": answer_author,
                "author_link": answer_author_link,
                "views": answer_views,
                "upvotes": answer_upvotes,
                "question_title": question_text,
                "question_link": urllib.parse.urljoin(BASE_URL, a),
            }
            answer_retrieved = True
            with open(ANSWER_OUTPUT_FILE, "a") as f:
                f.write("{}\n".format(json.dumps(new_data)))
            break
    return answer_retrieved


def process_user(driver, writer_url):
    '''
    - input: webdriver, the writer's url
    - desc: Processes each user's credential and their answers to questions.
            Adding them to users.json and answers.json
    - output: void
    '''
    url = urllib.parse.urljoin(BASE_URL, writer_url)
    try:
        print("Processing user: ", url)
        driver.get(url)
        time.sleep(3)
    except:
        print("Process user took too long! return: ")
        return

    # Test the existence of the user
    try:
        name_and_signature = driver.find_element_by_class_name('ProfileNameAndSig')
    except:
        print("User does not exist! Returning...")
        return

    # have to scroll until the end of page
    current_html = driver.find_element_by_class_name('ContentWrapper')
    current_html = current_html.get_attribute('innerHTML')
    stuck_value = 0
    disconnected = False
    while(True):
        if disconnected:
            print("REINITIALIZING WEB DRIVER")
            # Initialize webdriver
            driver = webdriver.PhantomJS()
            driver.maximize_window()
            driver.set_window_position(0, 0)
            driver.get('https://www.quora.com/')
            driver.set_page_load_timeout(30)

            # Login to Quora to scrape more information
            login(driver)
            driver.get(url)
            time.sleep(3)
            current_html = driver.find_element_by_class_name('ContentWrapper')
            current_html = current_html.get_attribute('innerHTML')
            disconnected = False

        prev_html = current_html
        # scroll to the end of page and set some delay --> to get the questions
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(8)
        try:
            current_html = driver.find_element_by_class_name('ContentWrapper')
            current_html = current_html.get_attribute("innerHTML")
        except:
            print("Remote connection has been closed, try reconnecting again...")
            disconnected = True
            continue

        if stuck_value > 5:
            break

        if prev_html == current_html:
            # if after scrolling nothing changes, that means it is stuck
            stuck_value += 1

    # add another delay here just to make sure all of them got loaded
    time.sleep(2)
    # have to get the info of each user
    try:
        name_and_signature = driver.find_element_by_class_name('ProfileNameAndSig')
    except:
        print("Cannot find name, skipping the user..")
        return
    name = name_and_signature.find_element_by_class_name('user').text
    try:
        description = name_and_signature.find_element_by_class_name('UserCredential').text
    except:
        description = ''
    try:
        credentials_and_highlights = driver.find_element_by_class_name('AboutSection')
    except:
        pass
    try:
        education = credentials_and_highlights.find_element_by_class_name('SchoolCredentialListItem')
        education = re.sub(r'Studied at', '', education.find_element_by_class_name('UserCredential').text).strip()
    except:
        education = ''
    try:
        lives_in = credentials_and_highlights.find_element_by_class_name('LocationCredentialListItem')
        lives_in = re.sub(r'Lives in', '', lives_in.find_element_by_class_name('UserCredential').text).strip()
    except:
        lives_in = ''
    try:
        work = credentials_and_highlights.find_element_by_class_name('WorkCredentialListItem')
        work = work.find_element_by_class_name('UserCredential')
    except:
        work = ''

    num_answers = int(re.sub('\D', '', driver.find_element_by_class_name('AnswersNavItem').find_element_by_class_name('list_count').text))
    num_questions = int(re.sub('\D', '', driver.find_element_by_class_name('QuestionsNavItem').find_element_by_class_name('list_count').text))
    num_posts = int(re.sub('\D', '', driver.find_element_by_class_name('PostsNavItem').find_element_by_class_name('list_count').text))
    num_blogs = int(re.sub('\D', '', driver.find_element_by_class_name('BlogsNavItem').find_element_by_class_name('list_count').text))
    num_followers = int(re.sub('\D', '', driver.find_element_by_class_name('FollowersNavItem').find_element_by_class_name('list_count').text))
    num_following = int(re.sub('\D', '', driver.find_element_by_class_name('FollowingNavItem').find_element_by_class_name('list_count').text))
    num_topics = int(re.sub('\D', '', driver.find_element_by_class_name('TopicsNavItem').find_element_by_class_name('list_count').text))

    new_data = {
        'author_name': name,
        'author_url': url,
        'description': description,
        'education': education,
        'lives_in': lives_in,
        'num_answers': num_answers,
        'num_questions': num_questions,
        'num_posts': num_posts,
        'num_blogs': num_blogs,
        'num_followers': num_followers,
        'num_following': num_following,
        'num_topics': num_topics
    }

    with open(USER_OUTPUT_FILE, "a") as f:
        f.write("{}\n".format(json.dumps(new_data)))
        print('AUTHOR ADDED: ', name)

    try:
        answers = driver.find_element_by_class_name('layout_3col_center')
        answers_soup = BeautifulSoup(answers.get_attribute("innerHTML").encode("utf-8"), 'html.parser')
        answers_links = answers_soup.find_all('a', class_='question_link')
        answers_links_href = []
    except:
        return

    for a in answers_links:
        answers_links_href.append(a['href'])
    # no answer at all, no need to collect anything
    if len(answers_links) == 0:
        return
    print('Begin collecting answers of: ', name)
    count_answers = 0
    for a in answers_links_href:
        try:
            driver.get(urllib.parse.urljoin(BASE_URL, a))
        except:
            # Just skip to the next question if something fails
            print("Getting answer error!")
            continue
        # Get question text
        # Process each answer, if an answer with the original author is found, break and finish
        try:
            answers = driver.find_element_by_class_name('AnswerListDiv')
        except:
            continue
        try:
            # question_text = driver.find_element_by_class_name('rendered_qtext').text.encode("utf-8")
            question = driver.find_element_by_class_name('QuestionTextInlineEditor')
            question_soup = BeautifulSoup(question.get_attribute('innerHTML').encode('utf-8'), 'html.parser')
            question_text = question_soup.find('span', class_='rendered_qtext').get_text()
            # answer_div.find('span', class_='rendered_qtext').get_text()
        except:
            continue

        finish_scroll_answer = process_answer_divs(answers, url, question_text, a)

        # reached here, cant find the author's answer
        current_html = driver.find_element_by_class_name('AnswerListDiv')
        stuck_value_answer = 0
        while not finish_scroll_answer:
            # print("test scrolling down...")
            prev_html = current_html
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            current_html = driver.find_element_by_class_name('AnswerListDiv')
            if stuck_value_answer > 15:
                print('stuck value answer too high, break')
                break
            if prev_html == current_html:
                stuck_value_answer += 1
            finish_scroll_answer = process_answer_divs(current_html, url, question_text, a)
        count_answers += 1
    print("Finished processing all answers for: ", name)
    print("Number of answers retrieved: ", count_answers)


def process_following(driver, writer_url):
    '''
    - Input: webdriver and a writer's url
    - Desc: Get all the users that a user follow and add it to the list
    - Output: void
    '''
    print('Now processing following section of: ', writer_url)
    url = urllib.parse.urljoin(BASE_URL, writer_url + '/following')
    print('url following is: ', url)
    try:
        driver.get(url)
    except TimeoutException as e:
        print("Process following took too long! returning: " + str(e))
        return
    # do infinite scrolling to get all the followers
    stuck_value = 0
    # have to scroll until the end of page
    try:
        current_html = driver.find_element_by_class_name('ContentWrapper')
    except:
        # user has no follower! just break
        print("user has no follower, returning...:")
        return
    current_html = current_html.get_attribute('innerHTML')

    while(True):
        prev_html = current_html
        # scroll to the end of page and set some delay --> to get the users in the following section
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        current_html = driver.find_element_by_class_name('ContentWrapper')
        current_html = current_html.get_attribute("innerHTML")
        time.sleep(3)

        if stuck_value > 3:
            break

        if prev_html == current_html:
            # if after scrolling nothing changes, that means it is stuck
            stuck_value += 1

    users = driver.find_element_by_class_name('layout_3col_center')
    users_soup = BeautifulSoup(users.get_attribute("innerHTML").encode("utf-8"), 'html.parser')
    users_links = users_soup.find_all('a', class_='user')
    # Find set difference
    fake_links = []
    fake_link_divs = users_soup.find_all('div', class_='UserFollowProofVisibleList')
    for link in fake_link_divs:
        fake_links.append(link.find('a')['href'])
    users_links = [u['href'] for u in users_links if u['href'] not in fake_links]
    for a in users_links:
        # if (a not in list_of_top_writers) and (a not in following_list):
            # with open(FOLLOWING_OUTPUT_FILE, "a") as f:
            #     # Add to file
            #     f.write("{}\n".format(json.dumps(a)))
        if a not in following_list and a not in list_of_writers:
            following_list.append(a)


def initialize():
    # Initialize webdriver
    print("Begin initializing connection to webdriver")
    driver = webdriver.PhantomJS()
    driver.maximize_window()
    driver.set_window_position(0, 0)
    driver.get(BASE_URL)
    driver.set_page_load_timeout(30)

    # Login to Quora to scrape more information
    login(driver)
    return driver


def finish(driver):
    # finish operation
    driver.close()
    driver.quit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Quora Scraper')
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('-u', '--username', type=str,
                       help='Crawl 1 specific user, return error if user is not found')
    group.add_argument('-v', '--usernames', type=str,
                       help='Crawl all usernames specified in a file (only json format separated by newline is supported!)')
    parser.add_argument('-f', '--following', action='store_true',
                        help='Add this flag to also crawl the data from the following section')
    args = parser.parse_args()
    driver = initialize()

    # Mode 1, only one user needs to be scraped
    if args.username is not None:
        username_url = '/profile/' + args.username
        process_user(driver, username_url)
        print('Finished getting all the answers for the user')
        if args.following:
            # Also crawl the following section of that user
            process_following(driver, username_url)
            # process users in following_list
            print('Users to be processed: ', len(following_list))
            for user in following_list:
                process_user(driver, user)

    # Mode 2, crawl all usernames specified in a file
    elif args.usernames is not None:
        try:
            f = open(args.usernames, 'r')
        except:
            print("File not found! Exiting program...")
        for line in f:
            list_of_writers.append('/profile/' + line.strip())
        for writer in list_of_writers:
            process_user(driver, writer)
        if args.following:
            # Also crawl the following section of that user
            for writer in list_of_writers:
                process_following(driver, writer)
            for user in following_list:
                process_user(driver, user)
    finish(driver)
