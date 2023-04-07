import pygame
from pyvidplayer import Video

pygame.init()
win = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()

#provide video class with the path to your video
vid = Video("Canon_D.mp4")

while True:
    for event in pygame.event.get():
	    if event.type == pygame.QUIT:
	    	vid.close()
	    	pygame.quit()
	    	exit()
    #draws the video to the given surface, at the given position
    vid.draw(win, (0, 0), force_draw=False)

    pygame.display.update()
