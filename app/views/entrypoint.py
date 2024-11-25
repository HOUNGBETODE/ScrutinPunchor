from views import MFA
from controllers.authentication import login, register
from controllers.authentication import MFA_generate
from controllers.utils import banner, menu_at_beginning, prompt, inform, pause


def show():
    """ Deals with user authentication : registration and login """

    banner()
    menu_at_beginning()

    match prompt():
        case "1":
            register()
            show()
        case "2":
            logged_user = login()
            if logged_user:
                user_id = logged_user[0]
                user_pseudo = logged_user[1]
                user_email = logged_user[2]
                MFA_generate(request_user_pseudo = user_pseudo)
                if pause():
                    MFA.show(user_pseudo = user_pseudo, user_id = user_id, user_email = user_email)
            else:
                if pause():
                    show()
        case _:
            exit("Choose a valid option (number only).")
