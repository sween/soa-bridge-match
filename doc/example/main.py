from windows import StudyWindow

BASEURL = "https://api.logicahealth.org/soaconnectathon30/open"


def run(subject_id, study_id="H2Q-MC-LZZT"):
    window = StudyWindow(BASEURL, study_id)
    protocol = window.get_protocol()
    processed = window.process_protocol(protocol)
    window.get_subject_scheme(subject_id, processed)
    


if __name__ == '__main__':
    STUDY_ID = "H2Q-MC-LZZT"
    SUBJECT_ID = "01-701-1111"
    run(SUBJECT_ID, STUDY_ID)
