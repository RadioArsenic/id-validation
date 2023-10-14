import cv2
import numpy as np
import pytesseract
import json
import re
import imghdr
import os

# TODO
"""
!Account for skewing

adding roi coords:
    ACT name roi (last is before first)
    TAS roi 

fixing roi:
    VIC, NT, SA all have errors
    account for long and short names


Cleaning data
    parse dates into same format (' ', '-', '/', '.')
            QLD does diff style to rest again
    name upper vs lower case
"""


class ImageConstantROI:
    class CCCD(object):
        AUSTRALIA_WA = {
            "name": [(45, 180, 155, 20), (19, 160, 120, 20)],
            "address": [(17, 199, 300, 40)],
            "expiry_date": [(17, 270, 140, 26)],
            "date_of_birth": [(200, 270, 140, 26)],
        }
        AUSTRALIA_VIC = {
            "name": [(14, 79, 350, 30)],
            "address": [(14, 128, 350, 90)],
            "expiry_date": [(14, 230, 150, 30)],
            "date_of_birth": [(217, 230, 150, 30)],
        }
        AUSTRALIA_NSW = {
            "name": [(12, 110, 250, 25)],
            "address": [(12, 175, 250, 50)],
            "expiry_date": [(465, 374, 150, 20)],
            "date_of_birth": [(280, 374, 150, 20)],
        }
        AUSTRALIA_NT = {
            "name": [(195, 168, 200, 25), (195, 145, 200, 25)],
            "address": [(195, 280, 200, 50)],
            "expiry_date": [(490, 371, 90, 20)],
            "date_of_birth": [(350, 371, 90, 20)],
        }
        # need name roi (last is before first)
        AUSTRALIA_ACT = {
            "name": [(110, 107, 54, 24), (12, 107, 96, 24)],
            "address": [(11, 126, 250, 60)],
            "expiry_date": [(252, 246, 130, 30)],
            "date_of_birth": [(115, 212, 140, 30)],
        }
        AUSTRALIA_SA = {
            "name": [(37, 209, 250, 25)],
            "address": [(16, 234, 250, 50)],
            "expiry_date": [(335, 100, 105, 30)],
            "date_of_birth": [(181, 100, 105, 30)],
        }
        AUSTRALIA_QLD = {
            "name": [(15, 86, 200, 25), (15, 62, 200, 25)],
            "expiry_date": [(347, 198, 75, 25)],
            "date_of_birth": [(215, 122, 120, 22)],
        }
        AUSTRALIA_TAS = {
            "name": [(230, 95, 140, 25), (230, 70, 90, 20)],
            "address": [(230, 125, 170, 55)], 
            "expiry_date": [(365, 280, 85, 15)],
            "date_of_birth": [(400, 220, 210, 30)],
        }
        AUSTRALIA_PASSPORT = {
            "name": [(210, 130, 130, 20), (210, 110, 100, 20)],
            "expiry_date": [(210, 265, 140, 20)],
            "date_of_birth": [(210, 185, 150, 20)],
        }


def cropImageRoi(image, roi):
    roi_cropped = image[
        int(roi[1]) : int(roi[1] + roi[3]), int(roi[0]) : int(roi[0] + roi[2])
    ]
    return roi_cropped

def preprocessing(image):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.multiply(gray, 1.5)

    # blur remove noise
    # blured = cv2.medianBlur(gray,3)
    blured1 = cv2.medianBlur(gray, 3)
    blured2 = cv2.medianBlur(gray, 51)
    divided = np.ma.divide(blured1, blured2).data
    normed = np.uint8(255 * divided / divided.max())

    # Threshold the image to convert non-black areas to white
    # _, thresholded = cv2.threshold(normed, 90, 255, cv2.THRESH_BINARY)
    th, thresholded = cv2.threshold(normed, 0, 255, cv2.THRESH_OTSU + cv2.THRESH_BINARY)

    # Create an all-white image of the same size as the original image
    result = np.ones_like(image) * 255

    # Copy the black areas from the original image to the result
    result[thresholded == 0] = image[thresholded == 0]

    # Save or display the resulting image
    cv2.imwrite("result_image.jpg", result)

    return result


def displayImage(image):
    cv2.imshow("Result Image", image)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def matchImage(image, baseImage):
    #Declare image size, width height and chanel
    baseH, baseW, baseC = baseImage.shape
    
    orb = cv2.ORB_create(1000)

    kp, des = orb.detectAndCompute(baseImage, None)
    
    PER_MATCH = 0.25

    #Detect keypoint on image
    kp1, des1 = orb.detectAndCompute(image, None)

    #Init BF Matcher, find the matches points of two images
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = list(bf.match(des1, des))

    #Select top 30% best matcher 
    matches.sort(key=lambda x: x.distance)
    best_matches = matches[:int(len(matches)*PER_MATCH)]

    #Show match img  
    imgMatch = cv2.drawMatches(image, kp1, baseImage, kp, best_matches,None, flags=2)
    displayImage(imgMatch)

    #Init source points and destination points for findHomography function.
    srcPoints = np.float32([kp1[m.queryIdx].pt for m in best_matches]).reshape(-1,1,2)
    dstPoints = np.float32([kp[m.trainIdx].pt for m in best_matches]).reshape(-1,1,2)


    #Find Homography of two images
    matrix_relationship, _ = cv2.findHomography(srcPoints, dstPoints,cv2.RANSAC, 5.0)

    #Transform the image to have the same structure as the base image
    img_final = cv2.warpPerspective(image, matrix_relationship, (baseW, baseH))

    displayImage(img_final)

    return img_final


def extract_information(image_path, location):
    information = {}

    # Load the image
    image = cv2.imread(image_path)

    # Resize Image
    resized_image = cv2.resize(image, (620, 413), interpolation=cv2.INTER_CUBIC)
    # displayImage(resized_image)

    for key, roi in getattr(ImageConstantROI.CCCD, location).items():
        data = ""
        for r in roi:
            crop_img = cropImageRoi(resized_image, r)
            # displayImage(crop_img)
            crop_img = preprocessing(crop_img)
            data += (
                pytesseract.image_to_string(
                    crop_img, config="--psm 6 --oem 3", lang="eng"
                )
                .replace("\n", " ")
                .strip()
                + " "
            )
        # displayImage(crop_img)
        information[key] = data.strip()
        # print(f"{key} : {data.strip()}")

        if location == "AUSTRALIA_SA" or location == "AUSTRALIA_ACT":
            parts = information["name"].split()
            information["name"] = f"{' '.join(parts[1:])} {parts[0]}"

    return information


# fine
# print(extract_information("./test_images/WA-driver-license.jpeg", "AUSTRALIA_WA"))
# print(extract_information("./test_images/NSW-driver-license.jpg", "AUSTRALIA_NSW"))
# print(extract_information("./test_images/ACT-driver-license.png", "AUSTRALIA_ACT"))
# print(extract_information("./test_images/QLD-driver-license.jpg", "AUSTRALIA_QLD"))

# VIC: reads "SAMPLE" as "SAMPLF"
# print(extract_information("./test_images/VIC-driver-license.jpg", "AUSTRALIA_VIC"))

# NT: "2 SAMPLE ST ROADSAFETY NT 0800" vs "'SSAMOLE ST ROACSAFLTY N7 C8IC", "25/12/1999" vs "25112:1999"
# print(extract_information("./test_images/NT-driver-license.png", "AUSTRALIA_NT"))

# SA: "1 FIRST ST ADELAIDE 5000" vs "1 FIRST S” ADELAIDE 50C0", "13/09/2014" vs "43709/2014", "14/09/1995" vs "14:99;1995"
# print(extract_information("./test_images/SA-driver-license.png", "AUSTRALIA_SA"))

# print(extract_information("./test_images/TAS-driver-license.jpeg", "AUSTRALIA_TAS"))

# '22 JUS 1979' vs 12 JUN 1979
# print(extract_information("./test_images/AUS Passport.jpg", "AUSTRALIA_PASSPORT"))

# WA: 'SUITE 2 120 BROADWAY SUITE 2 120 BROADW'VS'SUITE 2 120 BROADWAY CRAWLEY WA 6009, '20 Jul 202E'VS'20 Jul 2028, '45 Feb 20'VS'15 Feb 2001'
# print(extract_information("./test_images/WA-driver-license1.jpeg", "AUSTRALIA_WA"))


def date_builder(day, month, year):
    """helper function for date_detection. Formats the date"""
    return f"{day}-{month}-{year}"


def month_conversion(month):
    """helper function for date_detection. Converts the month from letter to number format"""
    r_month = ""
    month = month.upper()
    month_dict = {
        "JAN": "01",
        "FEB": "02",
        "MAR": "03",
        "APR": "04",
        "MAY": "05",
        "JUN": "06",
        "JUL": "07",
        "AUG": "08",
        "SEP": "09",
        "OCT": "10",
        "NOV": "11",
        "DEC": "12",
    }
    return month_dict.get(month, "00")


def date_detection(text):
    """a function to detect dates in a variety of forms and transform
    them into the typical dd-mm-yyyy format"""
    # an array to hold all discovered dates
    dates = []

    # regex patterns
    pattern = r"\b\d{16}\b"  # 16 numbers
    pattern2 = r"\d{2}[A-Za-z]{3}\d{4}"  # 10JUN1990
    pattern3 = r"[0-9]{2}-[A-Z]{3}-[0-9]{4}"  # 10-JUN-1990
    pattern4 = r"[0-9]{2}-[0-9]{2}-[0-9]{4}"  # 10-06-1990
    pattern5 = r"[0-9]{2}/[A-Z]{3}/[0-9]{4}"  # 10/JUN/1990
    pattern6 = r"[0-9]{2}/[0-9]{2}/[0-9]{4}"  # 10/09/1990
    pattern8 = r"\b\d{8}\b"  # 8 numbers

    # 16 numbers
    matches_16 = re.findall(pattern, text)
    for i in matches_16:
        j = i[8:]
        dates.append(date_builder(i[:2], i[2:4], i[4:8]))
        dates.append(date_builder(j[:2], j[2:4], j[4:8]))

    # 8 numbers
    matches_8 = re.findall(pattern8, text)
    for i in matches_8:
        dates.append(date_builder(i[:2], i[2:4], i[4:]))

    # ddMMMyyyy
    matches_3m = re.findall(pattern2, text)
    for i in matches_3m:
        month = month_conversion(i[2:5])
        dates.append(date_builder(i[:2], month, i[5:]))

    # dd-MMM-yyyy dd/MMM/yyyy
    matches_3dash = re.findall(pattern3, text)
    matches_3dash.extend(re.findall(pattern5, text))
    for i in matches_3dash:
        month = month_conversion(i[3:6])
        dates.append(date_builder(i[:2], month, i[7:]))

    # dd-mm-yyyy dd/mm/yyyy
    matches_2dash = re.findall(pattern4, text)
    matches_2dash.extend(re.findall(pattern6, text))
    for i in matches_2dash:
        dates.append(date_builder(i[:2], i[3:5], i[6:]))

    return dates


def validate_dates(dates):
    """ensures that all dates are valid. returns 0 if
    invalid date is present. if all dates are valid, returns
    the oldest date (date of birth)"""
    birthdate = ""
    year_check = 2101
    for i in dates:
        day = int(i[:2])
        month = int(i[3:5])
        year = int(i[6:])
        # checking date is valid
        if 32 < day < 0 or 13 < month < 0 or 2100 < year < 1900:
            return 0
        else:
            # if the current date is older than the stored date
            if year < year_check:
                birthdate = i
    return birthdate


def remove_file(image_path):
    """removes the file with the given image name.
    if the file is not an image, or the file does not exist, returns 1
    otherwise, returns 0"""
    # if the file doesnt exist, return error
    if not os.path.exists(image_path):
        return 1

    # if the file is not an image, return error
    f_type = imghdr.what(image_path)
    if not f_type:
        return 1

    # if the file exists, and is an image, delete it
    os.remove(image_path)
    return 0


# * INFO WANTED:
# name
# address
# expiry_date
# date_of_birth


def parsetoJSON(information):
    """Converts python dictionary to json. Returns 0 if error. Input is information from extract_information()"""
    if "address" in information:
        information["address"] = re.sub(",", "", information["address"])

    date = date_detection(information["expiry_date"])
    # ? not sure how the year check bit works?
    res = validate_dates(date)
    if res == 0:
        return 0
    information["expiry_date"] = "".join(str(x) for x in date)

    date = date_detection(information["date_of_birth"])
    # ? not sure how the year check bit works?
    res = validate_dates(date)
    if res == 0:
        return 0
    information["date_of_birth"] = "".join(str(x) for x in date)

    with open("id_data.json", "w", encoding="utf-8") as f:
        json.dump(information, f, indent=4)
