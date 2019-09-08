import os
import errno
import math as m
import time as t
import json as js
import requests as req

from tqdm import tqdm
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
import cfscrape as cfs
from bs4 import BeautifulSoup as soup

from kissnet import KissNet

DELAY_PER_VIDEO_ACCESS = 0
DELAY_PER_DOWNLOADS = 0

GECKO_DRIVER_PATH = "C:\geckodriver\geckodriver.exe"
KISSANIME_USERNAME = ""
KISSANIME_PASSWORD = ""
KISSASIAN_USERNAME = ""
KISSASIAN_PASSWORD = ""

def open_sub_file(subFile):
    try:
        with open(subFile) as jSub:
            data = js.load(jSub)
            print("subscription.json file opened")
            return data

    except FileNotFoundError:
        print("subscription.json file not found. Please ensure it is in the same directory as the program.")

def write_sub_file(subFile, data):
    try:
        with open(subFile, "w") as jSub:
            js.dump(data, jSub, indent=2)
            print("subscriptions.json file sucessfully updated")
    except FileNotFoundError:
        print("subscription.json file not found. Please ensure it is in the same directory as the program.")

def generate_sub_file(subFile):
    aSubTemplate = {
        'Title': 'insert_title_here',
        'Link' : 'insert_link_here',
        'AutoDL' : 'Yes/No',
        'Notif' : 'Yes/No'
    }

    subEmpty = {}
    subEmpty['subscriptions'] = []
    subEmpty['subscriptions'].append(aSubTemplate)

    try:
        with open(subFile, 'r+') as jSub:
            try:
                data = js.load(jSub)

                if('subscriptions' in data):
                    jSub.seek(0)
                    data['subscriptions'].append(aSubTemplate)
                    js.dump(data, jSub, indent=2)

            except:
                print("Error in subscription.json file. Attempting to overwrite file.")
                jSub.seek(0)
                js.dump(subEmpty, jSub, indent=2)

    except FileNotFoundError:
        print("subscriptions.json file not found. Attempting to write a new file.")

        with open(subFile, 'w') as jSub:
            js.dump(subEmpty, jSub, indent=2)

def init_driver():
    driver_path = GECKO_DRIVER_PATH
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options, executable_path=driver_path)
    print("Headless Firefox Driver Initialized")
    return driver

def close_driver(driver):
    driver.close()
    print("Headless Firefox Driver Closed")

def init_cfscraper():
    s = cfs.CloudflareScraper()
    print("CFScraper initialized")
    return s

def login(driver, kn):
    driver.get(kn.login_link())
    t.sleep(10)

    driver.find_element_by_name('username').send_keys(kn.username)
    driver.find_element_by_name('password').send_keys(kn.password)
    driver.find_element_by_id('btnSubmit').send_keys(Keys.ENTER)
    t.sleep(10)

    #check if login successful
    if driver.find_element_by_xpath("//a[@id='aDropDown']/span").text.__contains__(kn.username):
        print("Login successful")
        return True

    else:
        print("Login failed. Please check if your account information is correct.")
        return False

def goto_home(driver, kn):
    driver.get(kn.home_link())
    t.sleep(5)

def get_episode_links(cfscraper, kn, series):
    page = cfscraper.get(kn.series_link(series["Link"]))
    page_soup = soup(page.content, features="html.parser")

    status = page_soup.find_all("span", attrs={'class' : 'info'})
    for i, s in enumerate(status):
        if "Status" in s.text:
            status = s.next_sibling.strip()
    series["Status"] = status

    episode_table = page_soup.find("table", attrs={'class' : 'listing'})
    episode_table = episode_table.find_all("a")
    episode_links = []
    for ep in episode_table:
        episode = []
        link = ep["href"].replace("/" + kn.target + "/" + series["Link"] + "/", "")
        num = int(link[link.find("-")+1:link.find("?")])

        if (num >= series["Bookmark"]):
            episode.append(num)
            episode.append(link)
            episode_links.append(episode)
    
    if not "EpisodeLinks" in series:
        series["EpisodeLinks"] = []

    for ep in reversed(episode_links):
        series["EpisodeLinks"].append({"Num": ep[0], "Link": ep[1]})
        series["Bookmark"] = ep[0]
    
    print("Found " + str(len(episode_links)) + " new episodes!")
    series["Bookmark"] += 1

def get_download_link(driver, kn, series, loginstatus=False):
    if kn.target in {'Anime', 'Drama'}:
        for ep in series["EpisodeLinks"]:
            print(ep["Link"])
            driver.get(kn.episode_link(series["Link"], ep["Link"]))
            t.sleep(15)
            
            if loginstatus is True:
                print("logged in")
                ep["Linkmp4host"] = driver.find_element_by_xpath(kn.vid_containerpath(loginstatus)).get_attribute('href')
                print(ep["Linkmp4host"])
            
            else:
                print("Not logged in")
                driver.switch_to.frame(driver.find_element_by_id(kn.vid_containerpath(loginstatus)))
                ep["Linkmp4host"] = driver.find_element_by_id(kn.vid_mp4path(loginstatus)).get_attribute('src')
                print(ep["Linkmp4host"])
            
            t.sleep(DELAY_PER_VIDEO_ACCESS)

def download_file(series, loginstatus=False):
    home = ""

    for ep in series["EpisodeLinks"]:
        if not os.path.exists(os.path.dirname(home + series["Title"] + "/")):
            try:
                os.makedirs(os.path.dirname(home + series["Title"] + "/"))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

        with open(home + series["Title"] + "/" + series["Title"] + " EP" + "{0:02d}".format(ep["Num"]) + ".mp4", 'w') as f:
            print(ep["Linkmp4host"])
            if loginstatus is True:
                page = req.get(ep["Linkmp4host"], stream=True)
                page_soup = soup(page.content, features="html.parser")
                mp4link = page_soup.find("a", attrs={'class' : "button is-info is-outlined is-rounded"})["href"]
                r = req.get(mp4link, stream=True)
            else:
                r = req.get(ep["Linkmp4host"], stream=True)

            total_size = int(r.headers.get('content-length'))
            block_size = 1024
            print("File size: " + "{:.2f}".format(total_size/ 1048576) + "MB")
            
            written = 0
            for data in tqdm(r.iter_content(1024), total=m.ceil(total_size//block_size), unit="KB", unit_scale=True):
                written += len(data)
                f.write(data)
                f.flush()

            if total_size != 0 and written != total_size:
                print("Episode " + str(ep["Num"]) + " did not download fully. May be corrupted.")
            else:
                print("Episode " + str(ep["Num"]) + " sucessfully downloaded")

        t.sleep(DELAY_PER_DOWNLOADS)

def mode_grab_THEN_download():
    #Setup the sources
    KissAsianNet = KissNet("http://kissasian.sh", 'Login', 'Drama', "&s=rapid", KISSASIAN_USERNAME, KISSASIAN_PASSWORD)
    KissAnimeNet = KissNet("http://kissanime.ru", 'Login', 'Anime', "&s=rapidvideo", KISSANIME_USERNAME, KISSANIME_PASSWORD)
    
    LOGINSTATUS = True

    sources = open_sub_file("subscriptions.json")
    
    print("=== Episode Links ===")
    
    scraper = init_cfscraper()

    for source in sources["Sources"]:
        if not sources["Sources"][source]:
            print("Your subscription for " + source + " is empty.")

        else:
            for series in sources["Sources"][source]:
                print("Grabbing episode links for: " + series["Title"])
                if(source == "KissAnime"):
                    get_episode_links(scraper, KissAnimeNet, series)
                if(source == "KissAsian"):
                    get_episode_links(scraper, KissAsianNet, series)
            
            print("All episode links grabbed for: " + source)
    
    write_sub_file("subscriptions.json", sources)
    
    print("")
    print("=== Download Links ===")
    driver = init_driver()

    for source in sources["Sources"]:
        if not sources["Sources"][source]:
            print("Your subscription for " + source + " is empty.")

        else:
            if(source == "KissAsian"):
                KAsLogin = login(driver, KissAsianNet)
                t.sleep(10)
                goto_home(driver, KissAnimeNet)
                t.sleep(10)
            if(source == "KissAnime"):
                KAnLogin = login(driver, KissAnimeNet)
                t.sleep(10)
                goto_home(driver, KissAsianNet)
                t.sleep(10)

            for series in sources["Sources"][source]:
                print("Grabbing download links for: " + series["Title"])
                if(source == "KissAsian"):
                    get_download_link(driver, KissAsianNet, series, loginstatus=KAsLogin)
                if(source == "KissAnime"):
                    get_download_link(driver, KissAnimeNet, series, loginstatus=KAnLogin)

            print("All download links grabbed for: " + source)
    
    write_sub_file("subscriptions.json", sources)
    close_driver(driver)
    
    print("")
    print("=== Downloading Files ===")

    for source in sources["Sources"]:
        if not sources["Sources"][source]:
            print("Your subscription for " + source + " is empty.")

        else:
            for series in sources["Sources"][source]:
                print("Downloading files for: " + series["Title"])
                download_file(series, loginstatus=LOGINSTATUS)

            print("All files downloaded for: " + source)

    print("*** All files downloaded ***")

def mode_grab_AND_download():
    pass

if __name__ == '__main__':
    mode_grab_THEN_download()