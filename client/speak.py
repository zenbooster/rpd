from gtts import gTTS
import pygame
from time import sleep
tts = gTTS('Это же сон!', lang='ru')
tts.save('1.mp3')
pygame.mixer.init()
pygame.mixer.music.load(r'D:\git\RPD\client\1.mp3')
pygame.mixer.music.play()
sleep(5)