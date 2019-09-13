import os
import errno
import argparse as ap
import math as m
import time as t
import json as js
import requests as req

from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import *
import cfscrape as cfs
from bs4 import BeautifulSoup as soup
from tqdm import tqdm

from kissnet import KissNet

#=======================  USER SETTINGS  =======================
GECKO_DRIVER_PATH = r"C:/geckodriver/geckodriver.exe"
DOWNLOAD_LOCATION = r"C:/Users/Renzey/Downloads/KissMe/"
KISSANIME_USERNAME = "renzeydood"
KISSANIME_PASSWORD = "mark1992"
KISSASIAN_USERNAME = "renzeydood"
KISSASIAN_PASSWORD = "mark1992"

DELAY_PER_VIDEO_ACCESS = 0
DELAY_PER_DOWNLOADS = 0
#=======================  USER SETTINGS  =======================

def read_app_args():
    parser = ap.ArgumentParser()
    parser.add_argument("-s", "--subs", required=False, default="subscriptions.json", help="Subscription file to open. subscriptions.json is opened by default if left blank.")
    parser.add_argument("-m", "--mode", required=False, default="all", help="all= Default, it will search links and then download. searchEp= Only search and grabs new episode links. searchDl= Only search and grabs new download links for the episodes. download= Only download from links in json file.")
    parser.add_argument("-l", "--login", required=False, default="Y", help="Y= Login to the Kiss network and search for the download links (Default and recommended). Otherwise= Skips login step.")
    args = vars(parser.parse_args())
    return args

def open_sub_file(subFile):
    try:
        with open(subFile) as jSub:
            data = js.load(jSub)
            print(subFile + " file opened")
            return data

    except FileNotFoundError:
        print(subFile + " file not found. Please ensure it is in the same directory as the program.")

def write_sub_file(subFile, data):
    try:
        with open(subFile, "w") as jSub:
            js.dump(data, jSub, indent=2)
            print(subFile + " file sucessfully updated")

    except FileNotFoundError:
        print(subFile + " file not found. Please ensure it is in the same directory as the program.")

def clean_sub_file(subFile, data):
    pass

def init_driver():
    options = Options()
    options.headless = True
    driver = webdriver.Firefox(options=options, executable_path=GECKO_DRIVER_PATH)
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

    try:
        loginStatus = True if kn.username in driver.find_element_by_xpath("//a[@id='aDropDown']/span").text else False
    except NoSuchElementException as e:
        print("Failed to login.")
        loginStatus = False
    
    return loginStatus

def goto_home(driver, kn):
    driver.get(kn.home_link())
    t.sleep(5)

#Need to add error handling here
def get_episode_links(cfscraper, kn, series):
    page = cfscraper.get(kn.series_link(series["Link"]))
    page_soup = soup(page.content, features="html.parser")

    status = page_soup.find_all("span", attrs={'class' : 'info'})
    for s in status:
        if "Status" in s.text:
            status = s.next_sibling.strip()
    series["Status"] = status

    episode_table = page_soup.find("table", attrs={'class' : 'listing'}).find_all("a")
    episode_links = []
    for ep in episode_table:
        episode = []
        link = ep["href"].replace("/" + kn.target + "/" + series["Link"] + "/", "")
        if not series["Bookmark"] == 0:
            num = int(link[link.find("-")+1:link.find("?")])
        else:
            num = 0

        if (num >= series["Bookmark"]):
            episode.append(num)
            episode.append(link)
            episode_links.append(episode)
    
    if not "EpisodeLinks" in series:
        series["EpisodeLinks"] = []

    for ep in reversed(episode_links):
        series["EpisodeLinks"].append({"Num": ep[0], "Link": ep[1]})
    
    print("Found " + str(len(episode_links)) + " new episodes!")
    series["Bookmark"] += len(episode_links)

#Need to add error handling here
def get_download_link(driver, kn, series, loginstatus=False):
    if kn.target in {'Anime', 'Drama'}:
        for ep in series["EpisodeLinks"]:
            print(ep["Link"])
            driver.get(kn.episode_link(series["Link"], ep["Link"]))
            t.sleep(15)
            
            if loginstatus is True:
                ep["Linkmp4host"] = driver.find_element_by_xpath(kn.vid_containerpath(loginstatus)).get_attribute('href')
                print(ep["Linkmp4host"])
            
            else:
                driver.switch_to.frame(driver.find_element_by_id(kn.vid_containerpath(loginstatus)))
                ep["Linkmp4host"] = driver.find_element_by_id(kn.vid_mp4path(loginstatus)).get_attribute('src')
                print(ep["Linkmp4host"])
            
            t.sleep(DELAY_PER_VIDEO_ACCESS)

# Need to add error handling here
def download_file(ep, seriesName):
    home = DOWNLOAD_LOCATION
    status = False
    folderName = ""

    if ep["Num"] == 0:
        folderName = "Movies"
    else:
        folderName = seriesName

    if not os.path.exists(os.path.dirname(home + folderName + "/")):
        try:
            os.makedirs(os.path.dirname(home + folderName + "/"))
        except OSError as exc:
            if exc.errno != errno.EEXIST:
                raise
    
    fileTitle = seriesName + " EP" + "{0:02d}".format(ep["Num"])

    with open(home + folderName + "/" + fileTitle + ".mp4", 'wb') as f:
        print(fileTitle)
        if ep["Linkmp4host"].endswith(".mp4"):
            r = req.get(ep["Linkmp4host"], stream=True)
            
        else:
            page = req.get(ep["Linkmp4host"], stream=True)
            page_soup = soup(page.content, features="html.parser")
            mp4link = page_soup.find("a", attrs={'class' : "button is-info is-outlined is-rounded"})["href"]
            r = req.get(mp4link, stream=True)

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
            status = False
        else:
            print("Episode " + str(ep["Num"]) + " sucessfully downloaded")
            status = True

    t.sleep(DELAY_PER_DOWNLOADS)
    return status

def mode_grab_THEN_download():
    args = read_app_args()

    knet = {"KissAsian" : KissNet("http://kissasian.sh", 'Login', 'Drama', "&s=rapid", KISSASIAN_USERNAME, KISSASIAN_PASSWORD),
            "KissAnime" : KissNet("http://kissanime.ru", 'Login', 'Anime', "&s=rapidvideo", KISSANIME_USERNAME, KISSANIME_PASSWORD)}
    
    knetLogin = {"KissAsian" : False,
                 "KissAnime" : False}

    print("******** KISS ME START! ********")
    sources = open_sub_file(args["subs"])
    
    print("")

    if(args["mode"] == "all" or args["mode"] == "searchEp"):
        print("=== Episode Links ===")
        
        scraper = init_cfscraper()

        for source in sources["Sources"]:
            if not sources["Sources"][source]:
                print("Your subscription for " + source + " is empty.")

            else:
                for series in sources["Sources"][source]:
                    print("Grabbing episode links for: " + series["Title"])
                    get_episode_links(scraper, knet[source], series)
                
                print("All episode links grabbed for: " + source)
        
        write_sub_file(args["subs"], sources)
        
    print("")
    
    if(args["mode"] == "all" or args["mode"] == 'searchLink'):
        print("=== Download Links ===")
        driver = init_driver()

        for source in sources["Sources"]:
            if not sources["Sources"][source]:
                print("Your subscription for " + source + " is empty.")

            else:
                if(args["login"] == "Y"):
                    knetLogin[source] = login(driver, knet[source])
                    t.sleep(10)
                goto_home(driver, knet[source])
                t.sleep(10)

                for series in sources["Sources"][source]:
                    print("Grabbing download links for: " + series["Title"])
                    get_download_link(driver, knet[source], series, loginstatus=knetLogin[source])

                print("All download links grabbed for: " + source)
        
        write_sub_file(args["subs"], sources)
        close_driver(driver)
    
        print("")

    if(args["mode"] == "all" or args["mode"] == 'download'):
        print("=== Downloading Files ===")

        for source in sources["Sources"]:
            if not sources["Sources"][source]:
                print("Your subscription for " + source + " is empty.")

            else:
                for series in sources["Sources"][source]:
                    print("Downloading files for: " + series["Title"])
                    while(series["EpisodeLinks"]):
                        ep = series["EpisodeLinks"].pop(0)
                        if not download_file(ep, series["Title"]):
                            series["EpisodeLinks"].append(ep)
                        
                        write_sub_file(args["subs"], sources)
                        
                print("All files downloaded for: " + source)

        print("*** All files downloaded ***")
    
    for source in sources["Sources"]:
        if not sources["Sources"][source]:
            print("Your subscription for " + source + " is empty.")

        else:
            sources["Sources"][source][:] = [series for series in sources["Sources"][source] if not (series["Status"] == "Completed" and not series["EpisodeLinks"])]
    
    write_sub_file(args["subs"], sources)

    print("******** KISS ME STOPPED! ********")

def mode_grab_AND_download():
    pass

if __name__ == '__main__':
    mode_grab_THEN_download()