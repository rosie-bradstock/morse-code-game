import cv2
import mediapipe as mp
import pygame
import time

PINKY_FINGER_IDX = 20
MIDDLE_FINGER_IDX = 12
PALM_IDX = 9
THUMB_IDX = 4
TIME_UNIT = 0.25
MIN_SIGNAL_TIME = 0.8

morse_dict = {
    ".-": "A",
    "-...": "B",
    "-.-.": "C",
    "-..": "D",
    ".": "E",
    "..-.": "F",
    "--.": "G",
    "....": "H",
    "..": "I",
    ".---": "J",
    "-.-": "K",
    ".-..": "L",
    "--": "M",
    "-.": "N",
    "---": "O",
    ".--.": "P",
    "--.-": "Q",
    ".-.": "R",
    "...": "S",
    "-": "T",
    "..-": "U",
    "...-": "V",
    ".--": "W",
    "-..-": "X",
    "-.--": "Y",
    "--..": "Z",

    "-----": "0",
    ".----": "1",
    "..---": "2",
    "...--": "3",
    "....-": "4",
    ".....": "5",
    "-....": "6",
    "--...": "7",
    "---..": "8",
    "----.": "9"
}

# opening camera (0 for the default camera)
videoCap = cv2.VideoCapture(0)
playing_sound = False
beak_was_closed = True
handSolution = mp.solutions.hands
hands = handSolution.Hands(max_num_hands=1)
open_beak = False
previous_open_beak = False
state_start_time = time.time()
sentence = []
word = []
letter = []

cv2.namedWindow("CamOutput")
cv2.moveWindow("CamOutput", 300, 200)

pygame.mixer.init()
beep = pygame.mixer.Sound("beep.ogg")

def beak_closed(hand, previous_state):
    thumb = hand.landmark[THUMB_IDX]
    middle = hand.landmark[MIDDLE_FINGER_IDX]
    pinky = hand.landmark[PINKY_FINGER_IDX]
    middle_dist = ((thumb.x - middle.x) ** 2 + (thumb.y - middle.y) ** 2) ** 0.5
    pinky_dist = ((thumb.x - pinky.x) ** 2 + (thumb.y - pinky.y) ** 2) ** 0.5
    least_distance = min(middle_dist, pinky_dist)

    if least_distance < 0.06:
        return True
    elif least_distance > 0.10:
        return False
    else:
        return previous_state

def is_beak(hand):
    thumb = hand.landmark[THUMB_IDX]
    middle = hand.landmark[MIDDLE_FINGER_IDX]
    palm = hand.landmark[PALM_IDX]
    return (thumb.y > palm.y and abs(thumb.x - middle.x) < 0.20)

def is_horizontal(hand):
    tip = hand.landmark[MIDDLE_FINGER_IDX]
    base = hand.landmark[PALM_IDX]
    dx = abs(tip.x - base.x)
    dy = abs(tip.y - base.y)
    return dx > dy

while True:

    # allow quit
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

    # reading image
    success, img = videoCap.read()

    # showing image on separate window (only if read was successful)
    if success:

        # mirror the webcam
        img = cv2.flip(img, 1)
        imgRGB = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        # recognize hands from out image
        recHands = hands.process(imgRGB)
        if recHands.multi_hand_landmarks:
            for hand in recHands.multi_hand_landmarks:
                # draw the dots on each our image for visual help
                for datapoint_id, point in enumerate(hand.landmark):
                    h, w, c = img.shape
                    x, y = int(point.x * w), int(point.y * h)

                    if datapoint_id == 17:
                        cv2.circle(img, (x, y), 20, (255, 255, 255), cv2.FILLED)
                        cv2.circle(img, (x, y), 8, (0, 0, 0), cv2.FILLED)

                    else:
                        cv2.circle(img, (x, y), 2, (0, 0, 0), cv2.FILLED)

                # check for hand state
                beak_is_closed = beak_closed(hand, beak_was_closed)
                beak_was_closed = beak_is_closed

                # if beak is open
                if is_horizontal(hand) and not beak_is_closed and is_beak(hand):
                    open_beak = True

                    if not previous_open_beak:
                        current_time = time.time()
                        state_duration = current_time - state_start_time

                        # the closed state has just ended
                        if state_duration >= TIME_UNIT * 25:
                            if letter:
                                word.append("".join(letter))
                                letter.clear()
                            sentence.append(" ".join(word))
                            word.clear()

                        elif state_duration >= TIME_UNIT * 3:
                            word.append("".join(letter))
                            letter.clear()

                        state_start_time = current_time

                    if not playing_sound:
                        beep.play(loops=-1)
                        playing_sound = True

                # if beak is closed
                else:
                    open_beak = False

                    if previous_open_beak:
                        current_time = time.time()
                        state_duration = current_time - state_start_time

                        # the open state has just ended
                        if state_duration >= MIN_SIGNAL_TIME:
                            if state_duration < TIME_UNIT * 2:
                                letter.append(".")
                            else:
                                letter.append("-")

                        state_start_time = current_time

                    if playing_sound:
                        beep.stop()
                        playing_sound = False

                previous_open_beak = open_beak

        # handle if hand is moved off screen
        else:
            if playing_sound:
                beep.stop()
                playing_sound = False


        if cv2.waitKey(1) & 0xFF == ord('c'):
            letter.clear()
            word.clear()
            sentence.clear()

        # format the morse
        pretty_letter = " ".join(map(str, letter))

        pretty_word = " ".join(word)
        if letter:
            pretty_word += " " + "".join(letter)

        # write the morse to the screen
        cv2.putText(img, f'Letter: {pretty_letter}', (20, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        cv2.putText(img, f'Word: {pretty_word}', (20, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        # translate the morse to text
        translated_letter = ""
        if letter:
            translated_letter = morse_dict.get("".join(letter), "?")

        translated_word = ""
        for morse_letter in word:
            translated_word += morse_dict.get(morse_letter, "?")

        if letter:
            translated_word += morse_dict.get("".join(letter), "?")

        # write the text to the screen
        cv2.putText(img, f'Translation: {translated_letter}', (20, 120),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        cv2.putText(img, f'Word translation: {translated_word}', (20, 160),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 0), 2)

        #
        cv2.imshow("CamOutput", img)
        cv2.waitKey(1)

videoCap.release()
cv2.destroyAllWindows()
pygame.mixer.quit()
quit()