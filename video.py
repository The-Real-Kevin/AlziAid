import pygame
import random
from pyvidplayer import Video
import cv2
import mediapipe as mp
import time
import numpy as np

pygame.init()
win = pygame.display.set_mode((1280, 720))
clock = pygame.time.Clock()
pygame.display.set_caption("AlziAid V2.0")

#make some colors for the dots
blue = (0,0,255)
green = (0,255,0)
red = (255,0,0)

#provide video class with the path to your video
vid = Video("Canon_D.mp4")

#do some rng stuff
random.seed(1)

#opencv stuff


def mv_player():
	cap = cv2.VideoCapture(0)
	pTime=0
	mpDraw=mp.solutions.drawing_utils
	mpFaceMesh = mp.solutions.face_mesh
	faceMesh = mpFaceMesh.FaceMesh(max_num_faces = 1)
	drawSpec = mpDraw.DrawingSpec(thickness = 1, circle_radius = 1)
	cx = 640
	cy = 360
	vx = 5.0
	vy = 5.0
	while True:
		success, img = cap.read()
		imgRGB=cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
		results = faceMesh.process(imgRGB)
		if results.multi_face_landmarks:
			for faceLms in results.multi_face_landmarks: 
				mpDraw.draw_landmarks(img, faceLms, mpFaceMesh.FACEMESH_CONTOURS, drawSpec, drawSpec)
		cTime = time.time()
		fps=1/(cTime - pTime)
		pTime = cTime
		cv2.putText(img, f'FPS: {int(fps)}', (100, 100), cv2.FONT_HERSHEY_PLAIN, 5, (0, 255, 0), 5)
		cv2.imshow("Image", img)
		cv2.waitKey(1)
		for event in pygame.event.get():
			if event.type == pygame.QUIT:
				vid.close()
				pygame.quit()
				exit()
    		#draws the video to the given surface, at the given position
		vid.draw(win, (0, 0), force_draw=False)
		#cx = random.randint(100,1180)
		#cy = random.randint(100, 620)
		cx+=vx
		cy+=vy
		if cx>1250.0 or cx<30.0:
			vx*=-1.0
			vx+=(-0.5+random.random())
		if cy>690.0 or cy<30.0:
			vy*=-1.0
			vy+=(-0.5+random.random())
		pygame.draw.circle(win, blue, (cx, cy), 30)
		pygame.draw.circle(win, green, (cx+vx, cy+vy), 20)
		pygame.draw.circle(win, red, (cx+2*vx, cy+2*vy), 10)
		pygame.display.update()
		clock.tick(30)
		
		

mv_player()
