import PySimpleGUI as sg
import pathlib
import pickle
import base64
import requests
from tqdm import tqdm
import threading
import time
import pytz
from dateutil import parser
import httplib2
import webbrowser
import os

h = httplib2.Http()


def load_dct():
    with open("better_urls_fix.pkl", 'rb') as input:
        decoded = bytes(input.read())
    decoded = base64.b64decode(decoded)
    return pickle.loads(decoded)


courses_dct = load_dct()


def selector():
    layout = [
        [sg.Text('Please enter your course id!')],
        [sg.Text('ID', size=(15, 1)), sg.InputText('80131', key='-ID-')],
        [sg.Submit(), sg.Cancel()]
    ]
    window = sg.Window('Course details', layout)
    return mainloop(window)


def mainloop(window):
    while True:
        event, values = window.read()
        if not event or event == "Cancel":
            sg.popup("Goodbye.")
            window.close()
            exit()
        id = values['-ID-']
        if id in courses_dct:
            sg.popup(event, "Congratulations, we found your course! proceeding...")
            window.close()
            return id
        else:
            sg.popup(event, "Sorry, we can't find it")


def preferences(id):
    checkboxes = []
    for course in courses_dct[id]:
        for name, (lessons, year, semester, total_size_cams, total_all) in course.items():
            total_size_cams = round(total_size_cams, 2)
            total_all = round(total_all, 2)
            checkboxes.append([sg.Checkbox(f'{name}, {year}, {semester}, CAM: {total_size_cams} GB, TOTAL: {total_all} GB', default=False, key=name)])
    layout = [
        [sg.Text('Choose your download preferences', size=(30, 1), justification='center', font=("Helvetica", 25))],
        [sg.Frame(layout=checkboxes, title='Folders', title_color='red', relief=sg.RELIEF_SUNKEN)],
        [sg.Text('Do you want the screen files? AKA presentations in the PC')],
        [sg.Radio('Yes', "SCREEN", key='-SCREEN-'), sg.Radio('No', "SCREEN", default=True)],
        [sg.Text('Do you want to download the files or simply the urls?')],
        [sg.Radio('Download', "URL", default=True), sg.Radio('URLS', "URL", key='-URL-')],
        [sg.Submit(tooltip='Click to submit this form'), sg.Cancel()]
    ]
    window = sg.Window("Choose your preferences", layout)
    while True:
        event, values = window.read()
        if not event or event == "Cancel":
            window.close()
            main()
        folder = sg.popup_get_folder("Where do you want to save this?")
        if folder:
            break
    window.close()
    return values, folder


def download(url, fpath):
    """Download a file from the given url to the target file path.

    Parameters
    ----------
    url : str
        The url of the file to download.
    fpath : str
        The fully-qualified path where the file will be downloaded.
    """
    # Streaming, so we can iterate over the response.
    r = requests.get(url, stream=True)
    # Total size in bytes.
    total_size = int(r.headers.get('content-length', 0))
    block_size = 1024  # 1 Kibibyte
    t = tqdm(total=total_size, unit='iB', unit_scale=True)
    with open(fpath, 'wb') as f:
        for data in r.iter_content(block_size):
            t.update(len(data))
            f.write(data)
    t.close()
    if total_size != 0 and t.n != total_size:  # pragma: no cover
        print("Error! Something went wrong during download.")


def create_new_download_thread(url, fpath):
    download_thread = threading.Thread(target=download, args=(url, fpath))
    download_thread.start()


def download_threads(url, fpath, n_threads):
    for i in range(n_threads):
        create_new_download_thread(url, fpath)


def downloader(values, folder, id):
    for course in courses_dct[id]:
        for name, (lessons, year, semester, total_size_cams, total_all) in course.items():
            if not values[name]:
                continue
            course_name = name.replace('/', ',')
            if values['-URL-']:
                with open(rf"{folder}/{id} {year} {semester} {course_name}.txt", "w") as output:
                    sg.popup_no_buttons('Creating links... please wait', auto_close=True, non_blocking=True)
                    for lesson in lessons:
                        cam_url = lesson["PrimaryVideo"]
                        screen_url = lesson["SecondaryVideo"]
                        output.write(f"{cam_url}\n")
                        is_screen = True
                        resp = h.request(screen_url, 'HEAD')
                        if not int(resp[0]['status']) < 400:
                            is_screen = False
                        if values['-SCREEN-'] and is_screen:
                            output.write(f"{screen_url}\n")
                    sg.popup_no_buttons('Links for course created successfully, Proceeding', auto_close=True, non_blocking=True)
            else:
                for i, lesson in enumerate(lessons):
                    pathlib.Path(fr'{folder}/{name}').mkdir(parents=True, exist_ok=True)
                    cam_url = lesson["PrimaryVideo"]
                    screen_url = lesson["SecondaryVideo"]
                    date_str = lesson['CreationDate']
                    datetime_object = parser.parse(date_str)
                    israel = pytz.timezone('Israel')
                    date_local = israel.localize(datetime_object)
                    dt = date_local.strftime('%Y-%m-%d %H-%M')
                    title = f'{dt} {id}'
                    print(fr"Downloading... {folder}/{course}/{title}.mp4")
                    sg.popup_no_buttons(fr'Downloading {i + 1} cam of {len(lessons)}, please wait...', auto_close=True,
                             non_blocking=True)
                    download(cam_url, fr"{folder}/{name}/{title}.mp4")
                    sg.popup_no_buttons(fr'Downloading {i + 1} cam of {len(lessons)} successfully, proceeding...', auto_close=True,
                             non_blocking=True)
                    is_screen = True
                    resp = h.request(screen_url, 'HEAD')
                    if not int(resp[0]['status']) < 400:
                        is_screen = False
                    if values['-SCREEN-'] and is_screen:
                        sg.popup_no_buttons(fr'Downloading {i + 1} screen of {len(lessons)}, please wait...', auto_close=True,
                                 non_blocking=True)
                        download(screen_url, fr"{folder}/{course}/{title} screen.mp4")
                        sg.popup_no_buttons(fr'Downloading {i + 1} screen of {len(lessons)} successfully, proceeding...',
                                 auto_close=True, non_blocking=True)
    sg.popup_no_buttons("Check your Folder!", auto_close=True, non_blocking=True)
    webbrowser.open(os.path.realpath(folder))


def main():
    id = selector()
    values, folder = preferences(id)
    downloader(values, folder, id)
    time.sleep(2)


if __name__ == '__main__':
    main()
