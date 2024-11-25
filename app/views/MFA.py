from views import core
from termcolor import colored
from controllers.authentication import MFA_generate, MFA_verify
from controllers.utils import banner, pause, prompt, menu_for_MFA

def show(user_pseudo : str, user_id : int, user_email : str):
    """ Deals with user identity checking after raw login """

    banner()
    print(colored("(hids)@sp> Before going further into the steps, we need to verify your identity. A code has been sent to your email box. Check it and provide it (2). You can ask for a new one in case of potential issues or no reception (1).", "cyan"))
    menu_for_MFA()

    match prompt():
        case "1":
            MFA_generate(request_user_pseudo = user_pseudo)
            if pause():
                show(user_pseudo, user_id, user_email)
        case "2":
            request_user_code = input("Your code : ")
            login_status = MFA_verify(request_user_pseudo = user_pseudo, request_user_code = request_user_code)
            if login_status == "verified" and user_id:
                # print("LOGGED IN !!!")
                core.show(user_id, user_pseudo, user_email)
            else:
                show(user_pseudo, user_id, user_email)
        case _:
            exit("Choose a valid option (number only).")
