from celeryutils import task

from django.utils.encoding import force_text

from mkt.site.mail import send_html_mail_jinja
from mkt.users.models import UserProfile


@task
def send_mail(user_ids, subject, text_template, html_template):
    for user_id in user_ids:
        user = UserProfile.objects.get(pk=user_id)
        if not user.email:
            print 'Skipping: {0}, no email'.format(user.pk)
            continue

        # TODO: the Pre-Verification API goes in here if relevant.
        context = {}
        with user.activate_lang():
            send_html_mail_jinja(force_text(subject),
                text_template, html_template,
                context, recipient_list=[user.email])
