"""This module defines the global variables and paths used throughout the project"""
import os

main_db_path = 'C:\ProgramData\GOG.com\Galaxy\storage\galaxy-2.0.db'
gtt_profile_name = 'Aravind'
gtt_db_path = os.path.join('C:', os.sep, 'ProgramData', 'Gameplay Time Tracker', 'Userdata', 'Profiles',
                           gtt_profile_name,
                           'GameplayTimeTracker.sqlite')
platforms_json = 'data/platforms.json'
