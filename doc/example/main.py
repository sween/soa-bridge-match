from windows import StudyWindow

BASEURL = "https://api.logicahealth.org/soaconnectathon30/open"


def run(subject_id, study_id="H2Q-MC-LZZT"):
    window = StudyWindow(BASEURL, study_id)
    protocol = window.get_protocol()
    processed = window.process_protocol(protocol)
    subject_date = window.get_index_date(subject_id, processed)
    print(subject_date)


if __name__ == '__main__':
    STUDY_ID = "H2Q-MC-LZZT"
    SUBJECT_ID = "01-701-9999"
    run(SUBJECT_ID, STUDY_ID)
