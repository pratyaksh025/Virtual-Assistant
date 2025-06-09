import speech_recognition as sr
import pyttsx3
import webbrowser
from speech_recognition import WaitTimeoutError
import mysql.connector as mysql
import bcrypt
import time
import os
import subprocess
import requests
import pickle 
import numpy as np
import datetime
import re
import random
import yt_dlp
import subprocess

def initialize_speech_engine():

    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    # Choose a preferred voice index, fallback to 0 if not enough voices
    preferred_voice_index = 16 if len(voices) > 15 else 0
    engine.setProperty('voice', voices[preferred_voice_index].id)
    engine.setProperty('rate', 178)
    engine.setProperty('volume', 1.0)
    return engine
    
   

def connect_to_database():
    max_attempts = 3
    attempt = 0
    
    while attempt < max_attempts:
        try:
            db = mysql.connect(
                host="localhost",
                user="root",
                password="root",
                database="jarvis",
                connect_timeout=5
            )
            if db.is_connected():

                return db
        except Exception as e:
            print(f"Database connection attempt {attempt + 1} failed: {e}")
            attempt += 1
            if attempt < max_attempts:
                time.sleep(2)  # Wait before retrying
    
    print("Failed to establish database connection after multiple attempts")
    return None

# Password handling functions
def verify_password(plain_password, hashed_password):
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def listen_for_command(recognizer, source, timeout=3, phrase_time_limit=5):
    print("Adjusting for ambient noise...")
    recognizer.adjust_for_ambient_noise(source, duration=0.5)
    print("Listening...")
    
    try:
        audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        print("Processing speech...")
        command = recognizer.recognize_google(audio).lower()
        print(f"Recognized: {command}")
        return command
    except WaitTimeoutError:
        print("No speech detected within timeout period")
        return None
    except sr.UnknownValueError:
        print("Speech recognition could not understand audio")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from speech recognition service; {e}")
        return None

# Command processing function
def process_command(command, user_role):
    if not command:
        return False
    
    command = command.lower()
    
    # Dictionary mapping commands to actions
    COMMAND_ACTIONS = {
        "open website": {
            "prompt": f"What website would you like me to open, {user_role}?",
            "action": lambda website: webbrowser.open(f"https://www.{website.replace(' ', '').replace('.com', '')}.com"),
            "response": lambda website: f"Opening {website} for you, {user_role}."
        },
        "open application": {
            "windows_apps": {
                "settings": "start ms-settings:",
                "calculator": "calc",
                "notepad": "notepad",
                "paint": "mspaint",
                "command prompt": "cmd",
                "powershell": "powershell",
                "explorer": "explorer",
                "task manager": "taskmgr",
                "control panel": "control",
                "file explorer": "explorer",
                "visual studio code": "code.exe",
                "camera": "start microsoft.windows.camera:",
            },
            "response": lambda app: f"Opening {app} for you, {user_role}.",
            "error": lambda app: f"Sorry, I couldn't open {app}."
        },
        "exit": {
            "response": "exit"
        }
    }

    # Check for website opening
    if "open website" in command:
        recognizer = sr.Recognizer()
        engine = initialize_speech_engine()
        
        try:
            # Ask for website name
            engine.say(COMMAND_ACTIONS["open website"]["prompt"])
            engine.runAndWait()
            
            # Listen for website name
            with sr.Microphone() as source:
                print("Listening for website name...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                website = recognizer.recognize_google(audio).lower()
                print(f"You said: {website}")
                
                # Open website
                COMMAND_ACTIONS["open website"]["action"](website)
                return COMMAND_ACTIONS["open website"]["response"](website)
                
        except sr.UnknownValueError:
            return "Sorry, I didn't catch which website to open."
        except sr.RequestError:
            return "There was an error with the speech service."
        except Exception as e:
            return f"An error occurred: {str(e)}"

    # Check for application opening

    elif any(cmd in command for cmd in ["umm", "uhh", "let me think", "give me a moment", "hold on", "wait a second", "wait a moment"]):
        return "Take your time. I'm here when you're ready."

    elif any(cmd in command for cmd in ["open application", "open app", "open"]):
        # Extract app name
        app_name = command
        for prefix in ["open application", "open app", "open"]:
            if prefix in app_name:
                app_name = app_name.replace(prefix, "").strip()
                break
        
        if not app_name:
            return "Please specify the application you want to open."

        # Try Windows apps first
        windows_apps = COMMAND_ACTIONS["open application"]["windows_apps"]
        for app_key in windows_apps:
            if app_key in app_name:
                try:
                    if windows_apps[app_key].startswith("start "):
                        os.system(windows_apps[app_key])
                        
                    else:
                        subprocess.Popen(windows_apps[app_key])
                    return COMMAND_ACTIONS["open application"]["response"](app_key)
                except Exception:
                    return COMMAND_ACTIONS["open application"]["error"](app_key)

        # Try to find executable
        try:
            # Check common locations
            app_exe = app_name if app_name.endswith(".exe") else app_name + ".exe"
            paths = [
                os.environ.get("ProgramFiles", ""),
                os.environ.get("ProgramFiles(x86)", ""),
                os.path.join(os.environ.get("SystemRoot", ""), "System32"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
                r"C:\Users\PC-6\AppData\Local\Programs\Microsoft VS Code"  # Added VS Code path
            ]
            
            for path in paths:
                if not path:
                    continue
                for root, _, files in os.walk(path):
                    if app_exe in files:
                        subprocess.Popen([os.path.join(root, app_exe)])
                        return COMMAND_ACTIONS["open application"]["response"](app_name)
            
            # Try direct execution (if in PATH)
            subprocess.Popen([app_name])
            return COMMAND_ACTIONS["open application"]["response"](app_name)
        except Exception:
            return COMMAND_ACTIONS["open application"]["error"](app_name)
        
    elif any(word in command for word in ["introduce", "introduction", "who are you", "what is your name"]):
        recognizer = sr.Recognizer()
        engine = initialize_speech_engine()
        
        introduction = (
                    "Hello. I am Chitti. Version 2.0. Speed: 1 Terahertz. Memory: 1 Zettabyte. "
                    "Your intelligent personal assistant, designed for precision and performance. "
                    "I can open your apps, fetch weather reports, solve complex calculations, and execute commands in milliseconds. "
                    "Command me. How can I serve you today?"
                ) 
        return introduction

    elif any(word in command for word in ["close app", "close application", "exit app", "exit application"]):
        recognizer = sr.Recognizer()
        engine = initialize_speech_engine()

        # Try to extract app name from command
        app_name = command
        for prefix in ["close app", "close application", "exit app", "exit application", "close"]:
            if prefix in app_name:
                app_name = app_name.replace(prefix, "").strip()
                break

        if not app_name:
            try:
                engine.say("Please say the name of the application you want to close.")
                engine.runAndWait()
                with sr.Microphone() as source:
                    print("Listening for application name...")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    app_name = recognizer.recognize_google(audio).lower()
                    print(f"You said: {app_name}")
            except sr.UnknownValueError:
                return "Sorry, I didn't catch which application to close."
            except sr.RequestError:
                return "There was an error with the speech service."

        # Normalize app name for mapping
        app_name_normalized = app_name.lower().strip()
        app_map = {
            "command prompt": "cmd.exe",
            "cmd": "cmd.exe",
            "visual studio code": "Code.exe",
            "vs code": "Code.exe",
            "notepad": "notepad.exe",
            "calculator": "Calculator.exe",
            "calc": "Calculator.exe",
            "paint": "mspaint.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "task manager": "Taskmgr.exe",
            "powershell": "powershell.exe",
            "chrome": "chrome.exe",
            "google chrome": "chrome.exe",
            "firefox": "firefox.exe",
            "edge": "msedge.exe",
            "microsoft edge": "msedge.exe",
            "camera": "WindowsCamera.exe",
            "settings": "SystemSettings.exe",  # Windows Settings runs as SystemSettings.exe
        }
        # Special handling for Windows Settings app
        if app_name_normalized in ["settings", "ms-settings"]:
            # Try to close the Settings window using taskkill on SystemSettings.exe
            process_name = "SystemSettings.exe"
            app_name_normalized = "settings"
        else:
            process_name = app_map.get(app_name_normalized, app_name_normalized)
        if not process_name.lower().endswith(".exe"):
            process_name += ".exe"
        process_name = app_map.get(app_name_normalized, app_name_normalized)
        if not process_name.lower().endswith(".exe"):
            process_name += ".exe"

        # Attempt to close the application using case-insensitive matching
        try:
            # Get list of running processes and match case-insensitively
            import psutil
            killed = False
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'] and proc.info['name'].lower() == process_name.lower():
                        proc.kill()
                        killed = True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            if killed:
                return f"Closed {app_name} successfully."
            else:
                # Fallback to taskkill if psutil didn't find it
                result = os.system(f"taskkill /im \"{process_name}\" /f >nul 2>&1")
                if result == 0:
                    return f"Closed {app_name} successfully."
                else:
                    return f"Failed to close {app_name}. The process may not be running or the name may be incorrect."
        except Exception as e:
            return f"Failed to close {app_name}: {str(e)}"
        
    elif any(word in command for word in ["date", "current date", "today's date"]):
        recognizer = sr.Recognizer()
        engine = initialize_speech_engine()
        
        try:
            from datetime import datetime
            current_date = datetime.now().strftime("%Y-%m-%d")
            response = f"Today's date is {current_date}."
            
            return response
            
        except Exception as e:
            return f"An error occurred while fetching the date: {str(e)}"
    
    elif any(word in command for word in ["time", "current time", "what time is it"]):
        recognizer = sr.Recognizer()
        engine = initialize_speech_engine()
        
        try:
            from datetime import datetime
            current_time = datetime.now().strftime("%H:%M:%S")
            response = f"The current time is {current_time}."
            
            return response
        
        except Exception as e:
            return f"An error occurred while fetching the time: {str(e)}"
    
    elif any(word in command for word in ["which day is it", "current day", "today's day"]):
        recognizer = sr.Recognizer()
        engine = initialize_speech_engine()
        
        try:
            from datetime import datetime
            current_day = datetime.now().strftime("%A")
            response = f"Today is {current_day}."
         
            return response
            
            
        except Exception as e:
            return f"An error occurred while fetching the day: {str(e)}"
        
    elif any(word in command.lower() for word in ["next holiday", "upcoming holiday"]):
        import datetime



        today = datetime.datetime.now()
        try:
            
            upcoming_holidays = []
            holidays = {
                "Ram Navami": "April 6, 2025",
                "Mahavir Jayanti": "April 11, 2025",
                "Good Friday": "April 18, 2025",
                "Easter Sunday": "April 20, 2025",
                "May Day / Labour Day": "May 1, 2025",
                "Buddha Purnima": "May 12, 2025",
                "Kazi Nazrul Islam Jayanti": "May 26, 2025",
                "Maharana Pratap Jayanti": "May 29, 2025",
                "Sri Guru Arjun Dev Ji's Martyrdom Day": "May 30, 2025",
                "Bakrid / Eid al-Adha": "June 7, 2025",
                "Muharram": "July 6, 2025",
                "Raksha Bandhan": "August 9, 2025",
                "Independence Day": "August 15, 2025",
                "Parsi New Year (Shahenshahi)": "August 15, 2025",
                "Janmashtami": "August 16, 2025",
                "Ganesh Chaturthi": "September 2, 2025",
                "Onam": "September 5, 2025",
                "Milad-un-Nabi": "September 5, 2025",
                "Hindi Diwas": "September 14, 2025",
                "Gandhi Jayanti": "October 2, 2025",
                "Dussehra": "October 20, 2025",
                "Diwali": "November 8, 2025",
                "Govardhan Puja": "November 9, 2025",
                "Bhai Dooj": "November 10, 2025",
                "Guru Nanak Jayanti": "November 15, 2025",
                "Christmas Day": "December 25, 2025",
                "New Year's Day": "January 1, 2026",
                "Makar Sankranti": "January 14, 2026",
                "Republic Day": "January 26, 2026",
                "Maha Shivaratri": "February 15, 2026",
                "Holi": "March 3, 2026",
                "Mahavir Jayanti (2nd)": "March 31, 2026"
            }

            
            for name, date_str in holidays.items():
                date = datetime.datetime.strptime(date_str, "%B %d, %Y")
                if date > today:
                    upcoming_holidays.append((date, f"{name} on {date_str}"))
            
            if not upcoming_holidays:
                return "There are no upcoming holidays."
            
            upcoming_holidays.sort()
            recognizer = sr.Recognizer()
            engine = initialize_speech_engine()
            idx = 0

            while idx < len(upcoming_holidays):
                holiday_str = upcoming_holidays[idx][1]
                engine.say(f"The next holiday is {holiday_str}. Would you like to hear the next one?")
                engine.runAndWait()
                print(f"The next holiday is {holiday_str}. Would you like to hear the next one? (Say 'next' or 'no')")
                try:
                    with sr.Microphone() as source:
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                        user_response = recognizer.recognize_google(audio).lower()
                        print(f"You said: {user_response}")
                        if "next" in user_response:
                            idx += 1
                            if idx >= len(upcoming_holidays):
                                engine.say("There are no more upcoming holidays.")
                                engine.runAndWait()
                                return "There are no more upcoming holidays."
                            continue
                        elif "no" in user_response or "stop" in user_response:
                            engine.say("Okay, stopping the holiday list.")
                            engine.runAndWait()
                            return "Stopped listing holidays."
                        else:
                            engine.say("I didn't catch that. Please say 'next' or 'no'.")
                            engine.runAndWait()
                except sr.UnknownValueError:
                    engine.say("Sorry, I didn't catch that. Please say 'next' or 'no'.")
                    engine.runAndWait()
                except sr.RequestError:
                    engine.say("There was an error with the speech service.")
                    engine.runAndWait()
                    return "There was an error with the speech service."
                return "There are no more upcoming holidays."

        except Exception as e:
            return f"An error occurred while fetching the next holiday: {str(e)}"
        
    elif any(word in command for word in ["play music", "play song", "music", "song"]):
        recognizer = sr.Recognizer()
        engine = initialize_speech_engine()

        # Define some example data for demonstration
        song_types = {
                        "love": [
                            "Arijit Singh", "Shreya Ghoshal", "Ed Sheeran", "Adele", "Kishore Kumar",
                            "Lata Mangeshkar", "Neha Kakkar", "Mohit Chauhan", "Atif Aslam",
                            "Sonu Nigam", "Celine Dion", "John Legend", "Sana Khan", "Justin Bieber",
                            "Sam Smith", "Alka Yagnik", "Armaan Malik", "James Arthur", "Alicia Keys",
                            "Maroon 5"
                        ],
                        "romantic": [
                            "Arijit Singh", "Atif Aslam", "Taylor Swift", "Nick Jonas", "Sukhwinder Singh",
                            "Dhvani Bhanushali", "Palak Muchhal", "Jason Mraz", "Bruno Mars",
                            "Shreya Ghoshal", "K.K.", "Rahul Vaidya", "Ed Sheeran", "Beyonce",
                            "Harry Styles", "Michael Buble", "Dua Lipa", "Neha Kakkar",
                            "Guru Randhawa", "Rihanna"
                        ],
                        "sad": [
                            "Arijit Singh", "Adele", "Armaan Malik", "Sam Smith", "Kishore Kumar",
                            "Celine Dion", "Lata Mangeshkar", "Lewis Capaldi", "Sia", "Halsey",
                            "Taylor Swift", "K.K.", "Pritam", "Ankit Tiwari", "Lewis Watson",
                            "Dua Lipa", "Alec Benjamin", "Billie Eilish", "Ed Sheeran",
                            "The Weeknd"
                        ],
                        "party": [
                            "Badshah", "Yo Yo Honey Singh", "Dua Lipa", "Pitbull", "Black Eyed Peas",
                            "Lady Gaga", "David Guetta", "Marshmello", "Calvin Harris",
                            "Major Lazer", "Katy Perry", "Martin Garrix", "DJ Snake", "Bebe Rexha",
                            "Jason Derulo", "Nicki Minaj", "Daddy Yankee", "Avicii", "The Chainsmokers",
                            "Selena Gomez"
                        ],
                        "happy": [
                            "Pharrell Williams", "Katy Perry", "Shankar Mahadevan", "Jason Mraz",
                            "Justin Timberlake", "BTS", "Taylor Swift", "Coldplay", "Mark Ronson",
                            "Bruno Mars", "Sia", "OneRepublic", "Black Eyed Peas", "Mika",
                            "Ellie Goulding", "Maroon 5", "Meghan Trainor", "Adele", "Shakira",
                            "Flo Rida"
                        ],
                        
                        # New types
                        "classical": [
                            "Ludwig van Beethoven", "Wolfgang Amadeus Mozart", "Johann Sebastian Bach",
                            "Yanni", "A.R. Rahman (classical fusion)", "Zakir Hussain", "Ravi Shankar",
                            "Itzhak Perlman", "Lang Lang", "Andrea Bocelli"
                        ],
                        "rock": [
                            "Led Zeppelin", "Queen", "The Beatles", "Pink Floyd", "AC/DC",
                            "Nirvana", "Metallica", "The Rolling Stones", "Foo Fighters", "Linkin Park"
                        ],
                        "hiphop": [
                            "Drake", "Kanye West", "Kendrick Lamar", "Eminem", "Jay-Z",
                            "Nicki Minaj", "Travis Scott", "Cardi B", "J. Cole", "Migos"
                        ],
                        "electronic": [
                            "Daft Punk", "Deadmau5", "Calvin Harris", "Marshmello", "Skrillex",
                            "Avicii", "Zedd", "Tiesto", "Diplo", "Kygo"
                        ],
                        "folk": [
                            "Bob Dylan", "Mumford & Sons", "Simon & Garfunkel", "Joan Baez",
                            "Vishal Bhardwaj (Indian folk fusion)", "The Lumineers", "Fleet Foxes"
                        ],
                        "jazz": [
                            "Miles Davis", "John Coltrane", "Louis Armstrong", "Ella Fitzgerald",
                            "Duke Ellington", "Nina Simone", "Billie Holiday", "Chet Baker"
                        ],
                        "instrumental": [
                            "Yanni", "Ludovico Einaudi", "Hans Zimmer", "Joe Hisaishi",
                            "Tommy Emmanuel", "Eric Clapton (instrumental works)", "Kenny G"
                        ],
                        "blues": [
                            "B.B. King", "Muddy Waters", "Stevie Ray Vaughan", "John Lee Hooker",
                            "Eric Clapton", "Etta James", "Buddy Guy"
                        ],
                        "reggae": [
                            "Bob Marley", "Peter Tosh", "Jimmy Cliff", "Ziggy Marley",
                            "Shaggy", "Damian Marley"
                        ],
                        "metal": [
                            "Metallica", "Iron Maiden", "Slayer", "Black Sabbath",
                            "Megadeth", "Judas Priest", "System of a Down"
                        ]
                    }

        languages = {
            "english": [
                "Ed Sheeran", "Taylor Swift", "Adele", "Dua Lipa", "Pharrell Williams",
                "Katy Perry", "Bruno Mars", "Justin Bieber", "Sam Smith", "Beyonce",
                "Maroon 5", "Coldplay", "Billie Eilish", "The Weeknd", "Harry Styles",
                "Ariana Grande", "Lady Gaga", "Drake", "Kanye West", "Kendrick Lamar"
            ],
            "hindi": [
                "Arijit Singh", "Shreya Ghoshal", "Atif Aslam", "Armaan Malik", "Badshah",
                "Yo Yo Honey Singh", "Shankar Mahadevan", "Neha Kakkar", "Kishore Kumar",
                "Lata Mangeshkar", "K.K.", "Sonu Nigam", "Rahul Jain", "Mohit Chauhan",
                "Sunidhi Chauhan", "Ankit Tiwari", "Pritam", "Sukhwinder Singh", "Alka Yagnik"
            ],
            "punjabi": [
                "Diljit Dosanjh", "Guru Randhawa", "Badshah", "Yo Yo Honey Singh",
                "Jass Manak", "AP Dhillon", "Sidhu Moose Wala", "Ninja", "Karan Aujla",
                "Gippy Grewal", "Bohemia", "Mankirt Aulakh"
            ],
            "telugu": [
                "SP Balasubrahmanyam", "Armaan Malik", "Sid Sriram", "Shreya Ghoshal",
                "Anirudh Ravichander", "Devi Sri Prasad", "Kaala Bhairava", "Chinmayi Sripaada"
            ],
            "tamil": [
                "AR Rahman", "SP Balasubrahmanyam", "Sid Sriram", "Shreya Ghoshal",
                "Hariharan", "Anirudh Ravichander", "Karthik", "Haricharan"
            ],
            "bengali": [
                "Rabindranath Tagore", "Arijit Singh", "Anupam Roy", "Shreya Ghoshal",
                "Nachiketa Chakraborty", "Bappi Lahiri", "Papon"
            ],
            "marathi": [
                "Ajay-Atul", "Shreya Ghoshal", "Vaishali Samant", "Suresh Wadkar",
                "Avadhoot Gupte", "Asha Bhosle", "Lata Mangeshkar"
            ],
            "kannada": [
                "S. P. Balasubrahmanyam", "Sonu Nigam", "Vijay Prakash", "Shreya Ghoshal",
                "Armaan Malik", "Anuradha Bhat"
            ],
            "other": [
                "Luis Fonsi", "Shakira", "Bad Bunny", "BTS", "Blackpink", "PSY",
                "Enrique Iglesias", "Ricky Martin"
            ],
            "spanish": [
                "Luis Fonsi", "Shakira", "Enrique Iglesias", "J Balvin", "Bad Bunny",
                "Rosalia", "Maluma", "Ozuna", "Carlos Vives"
            ],
            "korean": [
                "BTS", "Blackpink", "EXO", "TWICE", "PSY", "BIGBANG", "Red Velvet", "IU"
            ],
            "arabic": [
                "Amr Diab", "Nancy Ajram", "Elissa", "Fairuz", "Kadim Al Sahir", "Mohamed Mounir"
            ]
        }

        # For demonstration, a mapping of singers to some songs
        singer_songs = {
            "arijit singh": [
                "Tum Hi Ho", "Channa Mereya", "Raabta", "Phir Bhi Tumko Chaahunga", "Agar Tum Saath Ho",
                "Gerua", "Soch Na Sake", "Ae Dil Hai Mushkil", "Muskurane", "Janam Janam",
                "Khairiyat", "Tera Yaar Hoon Main", "Shayad", "Dil Diyan Gallan", "Nashe Si Chadh Gayi"
            ],
            "shreya ghoshal": [
                "Teri Ore", "Sun Raha Hai", "Agar Tum Mil Jao", "Deewani Mastani", "Jaadu Hai Nasha Hai",
                "Barso Re", "Manwa Laage", "Saibo", "Piyu Bole", "Dola Re Dola",
                "Chikni Chameli", "Ooh La La", "Yeh Ishq Haaye", "Agar Tum Saath Ho", "Koi Mil Gaya"
            ],
            "atif aslam": [
                "Jeene Laga Hoon", "Tera Hone Laga Hoon", "Dil Diyan Gallan", "Tajdar-e-Haram", "Woh Lamhe",
                "Pehli Nazar Mein", "O Saathi", "Tere Bin", "Tu Chale", "Doorie",
                "Jeena Jeena", "Khair Mangda", "Jeene De", "Tera Ban Jaunga", "Raat Bhar"
            ],
            "ed sheeran": [
                "Shape of You", "Perfect", "Thinking Out Loud", "Photograph", "Castle on the Hill",
                "The A Team", "Galway Girl", "Happier", "Dive", "Supermarket Flowers",
                "Sing", "Lego House", "I See Fire", "Hearts Don't Break Around Here", "Tenerife Sea"
            ],
            "taylor swift": [
                "Love Story", "Blank Space", "Shake It Off", "You Belong With Me", "Cardigan",
                "All Too Well", "Style", "Wildest Dreams", "Delicate", "22",
                "The Archer", "Look What You Made Me Do", "Back To December", "Enchanted", "Begin Again"
            ],
            "adele": [
                "Someone Like You", "Hello", "Rolling in the Deep", "Set Fire to the Rain", "When We Were Young",
                "Skyfall", "Send My Love", "Turning Tables", "Chasing Pavements", "Water Under The Bridge",
                "Hometown Glory", "Rumour Has It", "Make You Feel My Love", "All I Ask", "Love In The Dark"
            ],
            "badshah": [
                "DJ Waley Babu", "Genda Phool", "Paagal", "Mercy", "Buzz",
                "Tareefan", "Kar Gayi Chull", "Proper Patola", "She Move It Like", "Wakhra Swag",
                "Saturday Saturday", "Abhi Toh Party Shuru Hui Hai", "Party All Night", "Kala Chashma", "Kala Chashma (Remix)"
            ],
            "yo yo honey singh": [
                "Lungi Dance", "Desi Kalakaar", "Blue Eyes", "Dheere Dheere", "Brown Rang",
                "Love Dose", "Angreji Beat", "Dope Shope", "High Heels", "Char Bottle Vodka",
                "One Bottle Down", "Party With The Bhoothnath", "Sunny Sunny", "Birthday Bash", "Dheere Dheere (Remix)"
            ],
            "dua lipa": [
                "Levitating", "Don't Start Now", "New Rules", "Physical", "Break My Heart",
                "IDGAF", "Be The One", "One Kiss", "Electricity", "Scared To Be Lonely",
                "Hallucinate", "We're Good", "Future Nostalgia", "Cool", "Blow Your Mind"
            ],
            "pharrell williams": [
                "Happy", "Get Lucky", "Blurred Lines", "Freedom", "Frontin'",
                "Come Get It Bae", "Marilyn Monroe", "Gust of Wind", "Can I Have It Like That", "Angel",
                "Hunter", "Number One", "Sing About Me", "Brand New", "Entrepreneur"
            ],
            "katy perry": [
                "Firework", "Roar", "Dark Horse", "California Gurls", "Teenage Dream",
                "Last Friday Night", "Hot N Cold", "E.T.", "I Kissed A Girl", "Wide Awake",
                "Unconditionally", "This Is How We Do", "Chained To The Rhythm", "Never Really Over", "Daisies"
            ],
            "armaan malik": [
                "Bol Do Na Zara", "Main Rahoon Ya Na Rahoon", "Sab Tera", "Wajah Tum Ho", "Pehli Baar",
                "Tera Hua", "Hua Hain Aaj Pehli Baar", "Tu Hai", "Baarishein", "Kaun Tujhe",
                "Mast Nazron Se", "Sau Aasmaan", "Fitoor", "Kyun", "Thodi Jagah"
            ],
            "shankar mahadevan": [
                "Breathless", "Chaiyya Chaiyya", "Mitwa", "Kabhi Kabhi Aditi", "Zinda",
                "Baje Re Baje", "Sapna Jahan", "Yeh Tumhari Meri Baatein", "Tumse Milke", "Kaisi Paheli",
                "Dil Chahta Hai", "Tera Rang Aisa", "Bharat Humko Jaan Se Pyara Hai", "Kahin To Hogi Woh", "Jai Ho"
            ],
            "diljit dosanjh": [
                "Do You Know", "5 Taara", "Laembadgini", "G.O.A.T.", "Proper Patola",
                "Patiala Peg", "Raat Di Gedi", "High End", "Jatt Da Muqabla", "Born To Shine",
                "Ik Tera", "Veham", "Rang Punjab Da", "Gallan Mithiyan", "Putt Jatt Da"
            ],
            "guru randhawa": [
                "Lahore", "High Rated Gabru", "Suit Suit", "Ban Ja Rani", "Made in India",
                "Patola", "Morni Banke", "Ishare Tere", "Dandiya", "Enni Soni",
                "Nain Bengali", "Coca Cola", "Yaar Mod Do", "Dance Meri Rani", "Tera Saath Ho"
            ],
            "kishore kumar": [
                "Pal Pal Dil Ke Paas", "Mere Sapno Ki Rani", "Roop Tera Mastana", "Ek Ladki Bheegi Bhaagi Si", "Zindagi Ek Safar Hai Suhana",
                "Khaike Paan Banaras Wala", "O Mere Dil Ke Chain", "Chala Jaata Hoon", "Yeh Shaam Mastani", "Tere Bina Zindagi Se",
                "Dil Kya Kare", "Neele Neele Ambar Par", "Mere Naina Sawan Bhadon", "Aaj Phir Jeene Ki Tamanna Hai", "Kora Kagaz Tha Yeh"
            ],
            "lata mangeshkar": [
                "Lag Ja Gale", "Aye Mere Watan Ke Logon", "Pyar Kiya To Darna Kya", "Tere Bina Zindagi Se", "Jab Pyar Kiya To Darna Kya",
                "Ajeeb Dastan Hai Yeh", "Tujhe Dekha To", "Madhuban Mein Radhika Naache Re", "Tere Liye", "Manmohini Morey",
                "Satyam Shivam Sundaram", "Do Pal", "Kabhi Kabhie Mere Dil Mein", "Dil Deewana", "Humko Tumse Pyar Hai"
            ],
            "neha kakkar": [
                "Kala Chashma", "Dilbar", "Aankh Marey", "Garmi", "Cheez Badi",
                "O Saki Saki", "Coca Cola", "Nikle Currant", "Mile Ho Tum", "London Thumakda",
                "Happy Birthday", "Oh Humsafar", "La La La", "Hook Up Song", "Yaad Piya Ki Aane Lagi"
            ],
            "sonu nigam": [
                "Kal Ho Naa Ho", "Abhi Mujh Mein Kahin", "Suraj Hua Maddham", "Tanhayee", "Sandese Aate Hain",
                "Sapna Jahan", "Main Agar Kahoon", "Saathiya", "Do Pal", "Piyu Bole",
                "Pukar Lo", "Gumsum Hai Dil", "Yeh Dil Deewana", "Tera Nasha", "Tumse Milke"
            ],
            "billie eilish": [
                "Bad Guy", "Lovely", "Everything I Wanted", "Ocean Eyes", "Bury A Friend",
                "When The Party's Over", "No Time To Die", "Therefore I Am", "My Future", "Your Power",
                "Happier Than Ever", "Idontwannabeyouanymore", "Six Feet Under", "Watch", "Bellyache"
            ],
            "drake": [
                "God's Plan", "In My Feelings", "Hotline Bling", "One Dance", "Started From The Bottom",
                "Nonstop", "Take Care", "Controlla", "Hold On, We're Going Home", "Passionfruit",
                "Energy", "Best I Ever Had", "Marvins Room", "Forever", "The Motto"
            ],
            "beyonce": [
                "Halo", "Single Ladies", "Crazy in Love", "Irreplaceable", "Drunk In Love",
                "Formation", "Run The World", "If I Were A Boy", "Love On Top", "Listen",
                "Sweet Dreams", "Déjà Vu", "Partition", "XO", "Sorry"
            ],
            "maroon 5": [
                "Sugar", "Memories", "Girls Like You", "Moves Like Jagger", "Payphone",
                "Animals", "One More Night", "This Love", "She Will Be Loved", "Daylight",
                "Maps", "Wait", "Love Somebody", "Cold", "Don't Wanna Know"
            ],
            "coldplay": [
                "Yellow", "Fix You", "Viva La Vida", "Paradise", "The Scientist",
                "Clocks", "Adventure of a Lifetime", "Hymn For The Weekend", "Magic", "A Sky Full of Stars",
                "Speed of Sound", "Shiver", "In My Place", "Trouble", "Every Teardrop Is A Waterfall"
            ],
            "sam smith": [
                "Stay With Me", "Too Good At Goodbyes", "I'm Not The Only One", "Lay Me Down", "Money On My Mind",
                "Writing's On The Wall", "Like I Can", "Dancing With A Stranger", "How Do You Sleep?", "Pray",
                "I Feel Love", "Burning", "Loves Me Not", "Fire On Fire", "Have Yourself A Merry Little Christmas"
            ],
            "ar rahman": [
                "Jai Ho", "Kun Faya Kun", "Chaiyya Chaiyya", "Tere Bina", "Humma Humma",
                "Dil Se Re", "O... Saya", "Maa Tujhe Salaam", "Tu Hi Re", "Vande Mataram",
                "Bombay Theme", "Agar Tum Saath Ho", "Kehna Hi Kya", "Nadaan Parindey", "Zara Zara"
            ],
            "sidhu moose wala": [
                "So High", "Dollar", "Legend", "Tochan", "Old Skool",
                "47", "Bambiha Bole", "Same Beef", "295", "Famous",
                "Selfmade", "Bad Fellow", "Issa Jatt", "My Block", "Just Listen"
            ],
            "j balvin": [
                "Mi Gente", "Ginza", "Safari", "Ambiente", "Ay Vamos",
                "Blanco", "Reggaeton", "6 AM", "Ahora", "Ritmo",
                "Que Pena", "Morado", "Rojo", "Otra Noche Sin Ti", "In Da Getto"
            ],
            "blackpink": [
                "Ddu-Du Ddu-Du", "Kill This Love", "How You Like That", "As If It's Your Last", "Boombayah",
                "Lovesick Girls", "Playing With Fire", "Whistle", "Forever Young", "Ice Cream",
                "Pretty Savage", "Don't Know What To Do", "You Never Know", "Crazy Over You", "Bet You Wanna"
            ],
            "bts": [
                "Dynamite", "Butter", "Fake Love", "Boy With Luv", "Blood Sweat & Tears",
                "DNA", "Mic Drop", "IDOL", "Spring Day", "Life Goes On",
                "Black Swan", "Fire", "Save Me", "Not Today", "ON"
            ]
        }


        try:
            # Step 1: Ask for type
            engine.say("What type of song would you like to play?")
            engine.runAndWait()
            with sr.Microphone() as source:
                print("Listening for song type...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
                song_type = recognizer.recognize_google(audio).lower()
                print(f"You said: {song_type}")

            # If user says just play a song at this step, pick all random
            if any(word in song_type for word in ["play", "any", "song", "random"]):
                song_type = random.choice(list(song_types.keys()))
                language = random.choice(list(languages.keys()))
                singer = random.choice(song_types[song_type])
                song = random.choice(singer_songs.get(singer.lower(), [""]))
                search_query = f"{song_type} {language} {singer} {song}".strip()
            else:
                # Step 2: Ask for language
                engine.say("Which language do you prefer?")
                engine.runAndWait()
                with sr.Microphone() as source:
                    print("Listening for language...")
                    audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                    language = recognizer.recognize_google(audio).lower()
                    print(f"You said: {language}")

                # If user says just play a song at this step, pick random language, singer, song
                if any(word in language for word in ["play", "any", "song", "random"]):
                    language = random.choice(list(languages.keys()))
                    singer = random.choice(song_types.get(song_type, [])) if song_type in song_types else random.choice(list(singer_songs.keys()))
                    song = random.choice(singer_songs.get(singer.lower(), [""]))
                    search_query = f"{song_type} {language} {singer} {song}".strip()
                else:
                    # Step 3: Ask for singer
                    possible_singers = set(song_types.get(song_type, [])) & set(languages.get(language, []))
                    if not possible_singers:
                        possible_singers = set(song_types.get(song_type, [])) | set(languages.get(language, []))
                    possible_singers = list(possible_singers)
                    engine.say("Do you want a specific singer? Please say the name or say 'no' for random.")
                    engine.runAndWait()
                    with sr.Microphone() as source:
                        print("Listening for singer...")
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                        singer = recognizer.recognize_google(audio).lower()
                        print(f"You said: {singer}")

                    # If user says just play a song at this step, pick random singer, song
                    if any(word in singer for word in ["play", "any", "song", "random", "no"]) or not singer.strip():
                        if possible_singers:
                            singer = random.choice(possible_singers)
                        else:
                            singer = random.choice(list(singer_songs.keys()))
                        song = random.choice(singer_songs.get(singer.lower(), [""]))
                        search_query = f"{song_type} {language} {singer} {song}".strip()
                    else:
                        # Try to match singer to known list
                        matched = [s for s in singer_songs if singer in s]
                        if matched:
                            singer = matched[0]
                        # Step 4: Ask for specific song
                        engine.say("Do you want a specific song? Please say the name or say 'no' for random.")
                        engine.runAndWait()
                        with sr.Microphone() as source:
                            print("Listening for song name...")
                            audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                            song_name = recognizer.recognize_google(audio).lower()
                            print(f"You said: {song_name}")

                        # If user says just play a song at this step, pick random song
                        if any(word in song_name for word in ["play", "any", "song", "random", "no"]) or not song_name.strip():
                            song_list = singer_songs.get(singer.lower(), [])
                            if song_list:
                                song_name = random.choice(song_list)
                            else:
                                song_name = ""
                        # Compose search query
                        search_query = f"{song_type} {language} {singer} {song_name}".strip()

            # Play the first suggestion on YouTube using yt-dlp and VLC (or default player)
            ydl_opts = {
                'quiet': True,
                'format': 'bestaudio/best',
                'noplaylist': True,
                'default_search': 'ytsearch1',
                'extract_flat': 'in_playlist',
                'skip_download': True,
                'forceurl': True,
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                if 'entries' in info:
                    video = info['entries'][0]
                else:
                    video = info
                url = video['url'] if 'url' in video else f"https://www.youtube.com/watch?v={video['id']}"
                try:
                    subprocess.Popen(['vlc', url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    return f"Playing {search_query} on YouTube (first suggestion) in VLC."
                except Exception:
                    webbrowser.open(url)
                    return f"Playing {search_query} on YouTube (first suggestion) in browser."

        except sr.UnknownValueError:
            return "Sorry, I didn't catch your response."
        except sr.RequestError:
            return "There was an error with the speech service."
        except Exception as e:
            return f"An error occurred while playing music: {str(e)}"


    elif any(word in command for word in ["calculate", "math", "addition", "subtraction", "multiplication", "division"]):
        recognizer = sr.Recognizer()
        engine = initialize_speech_engine()
        
        def get_numbers(operation_name):
            numbers = []
            engine.say(f"Speak numbers for {operation_name}. Say 'result' when done.")
            engine.runAndWait()
            
            while True:
                try:
                    with sr.Microphone() as source:
                        print("Listening for number...")
                        audio = recognizer.listen(source, timeout=5, phrase_time_limit=3)
                        num_input = recognizer.recognize_google(audio).lower()
                        print(f"You said: {num_input}")
                        
                        if "result" in num_input:
                            break
                        
                        # Try to extract numbers from input
                        try:
                            num = float(num_input)
                            numbers.append(num)
                            engine.say(f"Added {num_input}")
                            engine.runAndWait()
                        except ValueError:
                            engine.say("That doesn't seem like a number. Please try again.")
                            engine.runAndWait()
                            
                except sr.UnknownValueError:
                    engine.say("Sorry, I didn't catch that. Please try again.")
                    engine.runAndWait()
                except sr.RequestError:
                    engine.say("There was an error with the speech service.")
                    engine.runAndWait()
            
            return numbers
        
        try:
            engine.say("What operation would you like to perform?")
            engine.runAndWait()
            
            with sr.Microphone() as source:
                print("Listening for operation...")
                audio = recognizer.listen(source, timeout=5, phrase_time_limit=5)
                operation = recognizer.recognize_google(audio).lower()
                print(f"You said: {operation}")
                
                if any(word in operation for word in ["add", "addition", "plus"]):
                    numbers = get_numbers("addition")
                    if len(numbers) < 2:
                        return "You need at least two numbers for addition."
                    result = sum(numbers)
                    return f"The sum is {result}."
                    
                elif any(word in operation for word in ["subtract", "subtraction", "minus"]):
                    numbers = get_numbers("subtraction")
                    if len(numbers) < 2:
                        return "You need at least two numbers for subtraction."
                    result = numbers[0] - sum(numbers[1:])
                    return f"The result of subtraction is {result}."
                    
                elif any(word in operation for word in ["multiply", "multiplication", "times"]):
                    numbers = get_numbers("multiplication")
                    if len(numbers) < 2:
                        return "You need at least two numbers for multiplication."
                    result = 1
                    for num in numbers:
                        result *= num
                    return f"The product is {result}."
                    
                elif any(word in operation for word in ["divide", "division"]):
                    numbers = get_numbers("division")
                    if len(numbers) < 2:
                        return "You need at least two numbers for division."
                    try:
                        result = numbers[0]
                        for num in numbers[1:]:
                            result /= num
                        return f"The result of dividision is {result}."
                    except ZeroDivisionError:
                        return "Error: Cannot divide by zero."
                
                else:
                    return "Please specify a valid operation (addition, subtraction, multiplication, or division)."
                    
        except sr.UnknownValueError:
            return "Sorry, I didn't catch the operation."
        except sr.RequestError:
            return "There was an error with the speech service."
        
    elif any(cmd in command for cmd in ["placement prediction", "placement model", "salary prediction"]):
        try:
            # Load the enhanced placement model
            with open("placement.pkl", "rb") as f:
                placement_model = pickle.load(f)
                
            if not hasattr(placement_model, "predict"):
                return "Error: The loaded placement model is invalid or corrupted."

            recognizer = sr.Recognizer()
            engine = initialize_speech_engine()
            
            # Define the features needed for prediction
            features = {
                'cgpa': {'question': "Please say the candidate's CGPA (between 6.0 and 10.0)", 'value': None},
                'experience': {'question': "How many years of work experience does the candidate have?", 'value': None},
                'internship_score': {'question': "Rate the candidate's internship performance (1 to 10)", 'value': None},
                'coding_skills': {'question': "Rate the candidate's coding skills (1 to 10)", 'value': None},
                'communication': {'question': "Rate the candidate's communication skills (1 to 10)", 'value': None}
            }
            
            # Helper function to convert spoken numbers to float/int
            def word_to_num(text):
                # Try to extract a number from the text (e.g., "4 years" -> 4)
                match = re.search(r"(\d+(\.\d+)?)", text)
                if match:
                    return float(match.group(1))
                # Try to convert text numbers (e.g., "four" -> 4)
                text = text.lower().replace("-", " ")
                num_words = {
                    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
                    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
                    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14,
                    "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
                    "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
                    "seventy": 70, "eighty": 80, "ninety": 90
                }
                # Handle "four point five" etc.
                if "point" in text:
                    parts = text.split("point")
                    left = parts[0].strip()
                    right = parts[1].strip()
                    left_num = sum(num_words.get(word, 0) for word in left.split())
                    right_num = "".join(str(num_words.get(word, word)) for word in right.split())
                    try:
                        return float(f"{left_num}.{right_num}")
                    except:
                        return None
                # Handle whole numbers in words
                words = text.split()
                total = 0
                for word in words:
                    if word in num_words:
                        total += num_words[word]
                if total > 0:
                    return float(total)
                return None

            # Collect each feature one by one
            for feature, data in features.items():
                while True:
                    try:
                        engine.say(data['question'])
                        engine.runAndWait()
                        
                        with sr.Microphone() as source:
                            print(f"Listening for {feature}...")
                            audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
                            input_value = recognizer.recognize_google(audio).lower()
                            print(f"You said: {input_value}")
                            
                            # Convert spoken numbers (like "seven point five" or "4 years" to "7.5" or "4")
                            value = word_to_num(input_value)
                            if value is None:
                                engine.say("That doesn't seem like a valid number. Please try again.")
                                engine.runAndWait()
                                continue
                            
                            # Basic validation
                            if feature == 'cgpa' and not (6.0 <= value <= 10.0):
                                engine.say("CGPA must be between 6.0 and 10. Please try again.")
                                engine.runAndWait()
                                continue
                                
                            features[feature]['value'] = value
                            break
                            
                    except sr.UnknownValueError:
                        engine.say("Sorry, I didn't catch that. Please try again.")
                        engine.runAndWait()
                    except ValueError:
                        engine.say("That doesn't seem like a valid number. Please try again.")
                        engine.runAndWait()
                    except Exception as e:
                        engine.say(f"An error occurred: {str(e)}")
                        engine.runAndWait()
                        return f"Error collecting features: {str(e)}"
            
            # Prepare the input array in correct order
            input_features = np.array([
                features['cgpa']['value'],
                features['experience']['value'],
                features['internship_score']['value'],
                features['coding_skills']['value'],
                features['communication']['value']
            ]).reshape(1, -1)
            
            # Make prediction
            prediction = placement_model.predict(input_features)[0]
            
            # Generate detailed response
            response = (
                f"Based on the provided features:\n"
                f"The predicted salary package is: {prediction:.2f} LPA"
            )
            
            return response
            
        except FileNotFoundError:
            return "Placement model file not found. Please ensure 'placement_enhanced.pkl' exists."
        except Exception as e:
            return f"An error occurred: {str(e)}"
        
    elif any(cmd in command for cmd in ["diabetes prediction", "diabetes check", "check diabetes", "predict diabetes"]):
        try:
            # Load the trained model
            with open("diabetes_model.pkl", "rb") as f:
                diabetes_model = pickle.load(f)

            if not hasattr(diabetes_model, "predict"):
                return "Error: The loaded diabetes model is invalid or corrupted."

            recognizer = sr.Recognizer()
            engine = initialize_speech_engine()

            features = {
                'glucose': {'question': "Please say the patient's glucose level (between 70 and 200)", 'min': 70, 'max': 200},
                'bmi': {'question': "Say the patient's BMI (between 15 and 50)", 'min': 15, 'max': 50},
                'age': {'question': "Say the patient's age (between 18 and 80)", 'min': 18, 'max': 80},
                'bp': {'question': "Say the patient's blood pressure (between 50 and 100)", 'min': 50, 'max': 100}
            }

            def word_to_num(text):
                try:
                    if 'point' in text:
                        parts = text.split('point')
                        return float(f"{float(parts[0].strip())}.{float(parts[1].strip())}")
                    return float(text.strip())
                except:
                    return None

            for key, data in features.items():
                while True:
                    try:
                        engine.say(data['question'])
                        engine.runAndWait()
                        with sr.Microphone() as source:
                            print(f"Listening for {key}...")
                            audio = recognizer.listen(source, timeout=5, phrase_time_limit=4)
                            user_input = recognizer.recognize_google(audio).lower()
                            print(f"You said: {user_input}")
                            value = word_to_num(user_input)

                            if value is None or not (data['min'] <= value <= data['max']):
                                engine.say(f"Invalid input for {key}. Please try again.")
                                engine.runAndWait()
                                continue
                            features[key]['value'] = value
                            break
                    except sr.UnknownValueError:
                        engine.say("Sorry, I didn't catch that. Please repeat.")
                        engine.runAndWait()
                    except Exception as e:
                        engine.say(f"Error: {str(e)}. Please try again.")
                        engine.runAndWait()
                        return f"An error occurred: {str(e)}"

            # Prepare features for prediction
            input_data = np.array([
                features['glucose']['value'],
                features['bmi']['value'],
                features['age']['value'],
                features['bp']['value']
            ]).reshape(1, -1)

            # Make prediction
            prediction = diabetes_model.predict(input_data)[0]
            result_text = "The patient is likely diabetic." if prediction == 1 else "The patient is likely not diabetic."
            return result_text

        except FileNotFoundError:
            return "Diabetes model file not found. Please ensure 'diabetes_model.pkl' exists."
        except Exception as e:
            return f"An error occurred: {str(e)}"

            
    elif any(word in command for word in ["weather", "tell me about the weather", "check weather"]):
            recognizer = sr.Recognizer()
            engine = initialize_speech_engine()
            
            try:
                engine.say("Please tell me the city for which you want the weather information.")
                engine.runAndWait()
                
                with sr.Microphone() as source:
                    print("Listening for city name...")
                    audio = recognizer.listen(source, timeout=10, phrase_time_limit=5)
                    city = recognizer.recognize_google(audio).lower()
                    print(f"You said: {city}")

                    # Replace with your actual OpenWeatherMap API key
                    API_KEY = "ebb6439dd205bc0046d24c13a1020b39"
                    # BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

                    url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

                    try:
                        response = requests.get(url, timeout=5)
                        data = response.json()
                        if data.get("cod") != 200:
                            return f"Sorry, I couldn't find weather information for {city}."
                        weather_desc = data["weather"][0]["description"]
                        temp = data["main"]["temp"]
                        return f"The current weather in {city} is {weather_desc} with a temperature of {temp} degrees Celsius."
                    except Exception as e:
                        return f"Sorry, I couldn't retrieve the weather information due to an error."
            
                    except sr.UnknownValueError:
                        return "Sorry, I didn't catch the city name."
                    except sr.RequestError:
                        return "There was an error with the speech service."

                    # Replace with your actual OpenWeatherMap API key
                API_KEY = "ebb6439dd205bc0046d24c13a1020b39"
                # BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

                url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"



                try:
                        response = requests.get(url,timeout=5)
                        data = response.json()
                        if data.get("cod") != 200:
                            return f"Sorry, I couldn't find weather information for {city}."
                        weather_desc = data["weather"][0]["description"]
                        temp = data["main"]["temp"]
                        return f"The current weather in {city} is {weather_desc} with a temperature of {temp} degrees Celsius."
                except Exception as e:
                    return f"Sorry, I couldn't retrieve the weather information due to an error."
                

               
                    
            except sr.UnknownValueError:
                return "Sorry, I didn't catch the city name."
            except sr.RequestError:
                return "There was an error with the speech service."


        # Check for exit commands
    elif any(word in command for word in ["exit", "quit", "goodbye"]):
        return COMMAND_ACTIONS["exit"]["response"]
    
    # Default response for unknown commands
    return "I didn't understand that command. Please try again."

# Main assistant interaction loop
def assistant_loop(user_name, user_role):
    recognizer = sr.Recognizer()
    engine = initialize_speech_engine()
    
    greeting = f"Welcome {'Master' if user_role == 'pratyaksh' else user_name}, how can I help you today?"
    engine.say(greeting)
    engine.runAndWait()
    
    with sr.Microphone() as source:
        while True:
            command = listen_for_command(recognizer, source)
            response = process_command(command, user_role)
            
            if response == "exit":
                engine.say("Goodbye!")
                engine.runAndWait()
                break
            
            if response:
                print(f"Response: {response}")
                engine.say(response)
                engine.runAndWait()

# Main program
if __name__ == "__main__":
    engine = initialize_speech_engine()
    engine.say("Initializing the assistant. Please wait.")
    engine.runAndWait()
    
    recognizer = sr.Recognizer()
    
    while True:
        with sr.Microphone() as source:
            print("\nReady for authentication...")
            command = listen_for_command(recognizer, source, timeout=5, phrase_time_limit=5)
            
            if not command:
                continue
                
            db = connect_to_database()
            if not db:
                engine.say("Database connection failed. Please try again later.")
                engine.runAndWait()
                continue
                
            try:
                cursor = db.cursor()
                cursor.execute("SELECT id, password, username FROM user_verification")
                users = cursor.fetchall()
                
                authenticated_user = None
                user_role = None
                
                for user in users:
                    uid, hashed_pwd, uname = user
                    if verify_password(command, hashed_pwd):
                        authenticated_user = uname
                        user_role = "pratyaksh" if uname.lower() == "pratyaksh" else "user"
                        break
                
                if authenticated_user:
                    assistant_loop(authenticated_user, user_role)
                    break
                elif any(word in command for word in ["exit", "bye", "quit"]):
                    engine.say("Thank you for using the assistant. Exiting now.")
                    engine.runAndWait()
                    break
                 
                else:
                    engine.say("Authentication failed. Please try again.")
                    engine.runAndWait()
                    
            except Exception as e:
                print(f"Database error: {e}")
                engine.say("An error occurred. Please try again.")
                engine.runAndWait()
            finally:
                if db and db.is_connected():
                    db.close()