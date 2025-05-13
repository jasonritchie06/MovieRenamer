from __future__ import unicode_literals, print_function
import os
import tkinter as tk
from tkinter import filedialog
import tkinter.messagebox as msgbox
import re
from tmdbv3api import TMDb 
from tmdbv3api import Movie  
import ffmpeg  # requires ffmpeg to be installed via choco and ffmpeg-python via pip install
import mutagen # pip install mutagen. sudo apt install python3-mutagen.
import subprocess

tmdb = TMDb()

############################ Settings #################################################################
tmdb.api_key = ''    # get an api key and insert here for TMDB
tmdb.language = 'en'
tmdb.debug = True

debug = False   # set to True to not actually rename the files but print the results
update_meta = True  # set to True to update the media file meta data. May want to set to false for TV episodes
get_size = True     # set to True to get the size and insert into file name. i.e. 480p, 720p, 1080p, etc May want to set to false for TV episodes

#propEditPath = r"C:\Program Files\MKVToolNix\mkvpropedit.exe" # set this to the path containing mkvpropedit from the MKVToolnix install
propEditPath = "/usr/bin/mkvpropedit" # set this to the path containing mkvpropedit from the MKVToolnix install

lowers={'and', 'if', 'as', 'on', 'by', 'for', 'in', 'to', 'vs', 'unto', 
         'thru', 'a', 'with', 'or', 'but', 'versus', 'of', 'at', 'the', 'per',}

# add any keyword to this list that you want removed from the file names in your collection
keys = ['BRRIP', 'HDRIP', 'DVDSCR', 'WEBRIP', 'AMZN', 'DVDRIP', 'HDTV', 'MP4', 'NETFLIX', 'ESUB', 'MULTI', 'AVCHD', 'BLURAY', 'X264-HDC', 'BDRIP', 
        'BRIP', 'BG',  'AUDIO', 'HDTVRIP', 'UNRATED', 'HDDVD', 'REMUX', 'ENG', 'WEBDL', 'XVID', 'WEB DL']

# these are used to get a clean title to search tmdb while still keeping them in the file name. These get removed from the movie file name befor sending to TMDB
keys_clean = ['720P','1080P','X264', 'H264', '2160P', 'SD', 'UHD','DTS-X','AAC','AAC5','AC3','SD','6CH','EXTENDED','REMASTERED',
            '4K', 'UNRATED', 'HDR10', 'HDR10+', 'DDP2', 'DD5','HDR10PLUS','DTS-HDMA', 'BLURAY', 'IMAX', 'ATMOS','HD', 'HEVC','UHD', 'TRUEHD', 'DTS', 'DTS-HD', 'MA',
             'HDR', '480P', 'X265', 'H265', '5.1CH', '5.1', '7.1', '10BIT', 'BLU-RAY', 'DD5.1', '8ch', 'ULTRAHD', 'DD' , 'DTSX', 'DTSHD', 'AV1', 'MP3']

# movie title related words that should keep their case
cap_keys = ['HD', 'HEVC','UHD', 'TrueHD', 'DTS', 'DTS-HD', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VII', 'VIII', 'IX', 'DD', 'DDP', 'HDR', 
            'DTS-HDMA', 'BluRay', 'IMAX', 'ATMOS', 'HDR10Plus','DTS-X','AAC','AAC5','AC3','SD','6CH','EXTENDED','REMASTERED',
            '4K', 'UNRATED', 'HDR10', 'HDR10+', 'DDP2', 'DD5' , 'UltraHD', 'DTSX', 'DTSHD', 'MP3']

# list of file types we work with
vid_files= ['avi', 'mp4', 'mkv', 'm4v']

# standard encoding size list
enc_std_list  = ['2160p', '1080p', '720p', '480p', 'SD']

def lookup_standard(size):
    if 1600 <= size <= 3000:
        return "2160p"
    elif 750 <= size <= 1600:
        return "1080p"
    elif 500 <= size <= 750:
        return "720p"
    elif 390 <= size <= 500:
        return "480p"
    else:
        return "SD"

def has_enc_std(filename):
    for std in enc_std_list:
        if std in filename:
            return True
        
    return False
            
def get_movie_height(filename):
    print("getting movie resolution...")
    try:
        probe = ffmpeg.probe(filename)
    except ffmpeg.Error as e:
        print(e.stderr)
        return None

    video_stream = next((stream for stream in probe['streams'] if stream['codec_type'] == 'video'), None)
    if video_stream is not None:
        height = int(video_stream['height'])
        print("done...")
        return height
    else:
        return None

def get_clean_title(title):
    print("getting clean title:" + title )
    temp_title = ""
    title = title.split(' ')
    for word in title:
                tword = word.strip()
                if not tword.upper() in keys_clean:
                    temp_title += tword + " "
    print("done...")
    return temp_title

def get_date(title):
    print("getting movie date...")
    movie = Movie()
    thisMovie = title
    print("Getting " + thisMovie + " date...")
    m = movie.search(thisMovie)
    if m["total_results"] != 0 :
        for movie in m:
            if movie["release_date"]:
                print("done ...")
                return movie["release_date"].split('-')[0]
    else:
        return "None"

def title_capitalize(match, use_lowers=True):
    text=match.group()
    lower=text.lower()
    if lower in lowers and use_lowers==True:
        return lower
    else:
        i=0
        new_text=""
        capitalized=False
        while i<len(text):
            if text[i] not in {"’", "'"} and capitalized==False:
                new_text+=text[i].upper()
                capitalized=True
            else:
                new_text+=text[i].lower()
            i+=1
        return new_text

def title(the_string):
    first=re.sub(r"[\w'’‑-]+", title_capitalize, the_string)
    return re.sub(r"(^[\w'’‑-]+)|([\w'’‑-]+$)", lambda match : title_capitalize(match, use_lowers=False), first)

def rename_files(directory):
    for filename in os.listdir(directory):
        if os.path.isfile(os.path.join(directory, filename)):
            new_name = filename.lower()
            new_name = new_name.replace('.', ' ', new_name.count('.') -1)
            new_name = new_name.replace('_', ' ')
            new_name = new_name.replace('-', ' ')
              
            #print("new_name before title():" + new_name ) # uncomment for debugging
            new_name = title(new_name)
            new_name = new_name[0].upper() + new_name[1:] # always ensure the first letter in the title is capitalized
            print("new_name:" + new_name)
            name_split = new_name.split('.')
            ext = name_split[1].lower()
            words = name_split[0].split(' ')
            temp_word = ""
            temp_name = ""
            for word in words:
                temp_word = word.strip()
                if not temp_word.upper() in keys:
                    #print("temp_word:" + temp_word)
                    for ckey in cap_keys:
                        if ckey.lower() == temp_word.lower():
                            temp_word = ckey
  
                    if temp_word.isdigit() and len(temp_word) == 4 and not new_name.startswith(temp_word):
                        if temp_word.startswith('19') or temp_word.startswith('20'):
                            temp_word = "(" + temp_word + ")"
                        elif temp_word == "1080":
                            temp_word = temp_word + "p"

                    if temp_word == "720" and not new_name.startswith(temp_word):
                        temp_word = temp_word + "p"

                    if temp_word == "480" and not new_name.startswith(temp_word):
                        temp_word = temp_word + "p"

                    if temp_word.startswith("[19") and temp_word.endswith("]") and len(temp_word) == 6:
                        temp_word = "(" + temp_word[1:-1] + ")" # replace dates with []
                    
                    if temp_word.startswith("[20") and temp_word.endswith("]") and len(temp_word) == 6:
                        temp_word = "(" + temp_word[1:-1] + ")" # replace dates with []

                    if temp_word.endswith(')') and not temp_word.startswith('('):
                        temp_word = temp_word[:-1] # remove orphan parens

                    if temp_word.startswith('(') and not temp_word.endswith(')'):
                        temp_word = temp_word[1:] # remove orphan parens

                    if temp_word.upper().startswith('X264-'):
                        temp_word = 'X264'
                    
                    if temp_word.upper().startswith('AC3-'):
                        temp_word = 'AC3'

                    if temp_word.upper().startswith('AV1-'):
                        temp_word = 'AV1'

                    if temp_word.upper().startswith('X265-'):
                        temp_word = 'X265'
                        
                    if temp_word.upper().startswith('MP3-'):
                        temp_word = 'MP3'

                    if not temp_word == " ": temp_name += temp_word + " "

            # custom post processing fixes not covered in code above
            new_name = temp_name.strip()
            new_name = new_name.replace(' 5 1', ' 5.1')
            new_name = new_name.replace(' 7 1', ' 7.1')
            new_name = new_name.replace(' DD5 1', ' DD5.1')
            new_name = new_name.replace(' Ddp5 1', ' DDP5.1')
            new_name = new_name.replace(' Dd+5 1', ' DD5.1')
            new_name = new_name.replace(' AAC5 1', ' AAC 5.1')
            new_name = new_name.replace(' AAC5.1', ' AAC 5.1')
            new_name = new_name.replace(' Aac2 0', ' AAC2.0')
            new_name = new_name.replace(' DD5  1', ' DD5.1')
            new_name = new_name.replace(' DDP2 0', ' DDP2.0')
            new_name = new_name.replace(' H 264', ' H264')
            new_name = new_name.replace(' 2160 ', ' 2160p ')
            new_name = new_name.replace(' [1080p]', ' 1080p ')
            new_name = new_name.replace(' 1080p,', ' 1080p ')
            new_name = new_name.replace(' Bluray-1080p', ' Bluray 1080p ')
            new_name = new_name.replace(' Dd+7 1', ' DD+7.1')
            new_name = new_name.replace(' Mkv', '')
            new_name = new_name.replace(' Mp4', '')
            new_name = new_name.replace(' - ', ' ')
            new_name = new_name.replace("-", "")
            new_name = new_name.replace('  ', ' ')
            new_name = new_name.replace('Web Dl', '')

            just_title = get_clean_title(new_name)
            if not "(19" in new_name and not "(20" in new_name:
                mdate = get_date(just_title)
                if mdate:
                    if mdate != "None":
                        new_name += " (" + str(mdate) + ")"

            if not has_enc_std(new_name) and get_size == True:
                if ext in vid_files:
                    height = get_movie_height(os.path.join(directory, filename))
                    if height:
                       new_name += " " + lookup_standard(height)

            new_name = new_name + '.' + ext # putting file back together
            FilePath = os.path.join(directory, new_name)
            if not os.path.exists(FilePath):   # can't rename a file to the same name. In case we didn't change the file name
                if not debug == True:
                    os.rename(os.path.join(directory, filename), FilePath)
                    if update_meta:
                        if ext.upper() == "MP4":
                            print("updating MP4 title...")
                            with open(FilePath, 'r+b') as file:
                                media_file = mutagen.File(file, easy=True)
                                media_file['title'] = just_title
                                media_file.save(file)
                                print("done...")
                        elif ext.upper() == "MKV":
                            if os.path.exists(propEditPath):
                                print("updating MKV title...")
                                propCommand = propEditPath + ' "' + FilePath + '" --edit info --set "title=' + just_title + '"'
                                subprocess.run(propCommand)
                                print("done...")
                            else:
                                print("mkvtoolnix install not found. Cannot set mkv title.")
                print(filename + " renamed to: " + os.path.join(directory, new_name))   # to test without renaming files

def select_directory():
    directory = filedialog.askdirectory()
    rename_files(directory)
    msgbox.showinfo("Info", "Done.")

root = tk.Tk()
root.title("Movie Renamer")
root.geometry("250x174")
button = tk.Button(root, text="Select Directory", command=select_directory)
button.pack(side="bottom")
root.mainloop()
