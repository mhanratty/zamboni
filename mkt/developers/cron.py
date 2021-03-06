import datetime
import logging

import cronjobs
from celery.task.sets import TaskSet
from tower import ugettext as _

import amo
import lib.iarc
from amo.utils import chunked
from mkt.constants.iarc_mappings import RATINGS
from mkt.developers.tasks import (refresh_iarc_ratings, region_email,
                                  region_exclude)
from mkt.reviewers.models import RereviewQueue
from mkt.webapps.models import AddonExcludedRegion, Webapp


log = logging.getLogger('z.mkt.developers.cron')


def _region_email(ids, regions):
    ts = [region_email.subtask(args=[chunk, regions])
          for chunk in chunked(ids, 100)]
    TaskSet(ts).apply_async()


@cronjobs.register
def send_new_region_emails(regions):
    """Email app developers notifying them of new regions added."""
    excluded = (AddonExcludedRegion.objects
                .filter(region__in=[r.id for r in regions])
                .values_list('addon', flat=True))
    ids = (Webapp.objects.exclude(id__in=excluded)
           .filter(enable_new_regions=True)
           .values_list('id', flat=True))
    _region_email(ids, regions)


def _region_exclude(ids, regions):
    ts = [region_exclude.subtask(args=[chunk, regions])
          for chunk in chunked(ids, 100)]
    TaskSet(ts).apply_async()


@cronjobs.register
def exclude_new_region(regions):
    """
    Update regional blacklist based on a list of regions to exclude.
    """
    excluded = set(AddonExcludedRegion.objects
                   .filter(region__in=[r.id for r in regions])
                   .values_list('addon', flat=True))
    ids = (Webapp.objects.exclude(id__in=excluded)
           .filter(enable_new_regions=False)
           .values_list('id', flat=True))
    _region_exclude(ids, regions)


@cronjobs.register
def process_iarc_changes(date=None):
    """
    Queries IARC for recent changes in the past 24 hours (or date provided).

    If date provided use it. It should be in the form YYYY-MM-DD.

    NOTE: Get_Rating_Changes only sends the diff of the changes
    by rating body. They only send data for the ratings bodies that
    changed.
    """
    if not date:
        date = datetime.date.today()
    else:
        date = datetime.datetime.strptime(date, '%Y-%m-%d').date()

    client = lib.iarc.client.get_iarc_client('services')
    xml = lib.iarc.utils.render_xml('get_rating_changes.xml', {
        'date_from': date - datetime.timedelta(days=1),
        'date_to': date,
    })
    resp = client.Get_Rating_Changes(XMLString=xml)
    data = lib.iarc.utils.IARC_XML_Parser().parse_string(resp)

    for row in data.get('rows', []):
        iarc_id = row.get('submission_id')
        if not iarc_id:
            log.debug('IARC changes contained no submission ID: %s' % row)
            continue

        try:
            app = Webapp.objects.get(iarc_info__submission_id=iarc_id)
        except Webapp.DoesNotExist:
            log.debug('Could not find app associated with IARC submission ID: '
                      '%s' % iarc_id)
            continue

        try:
            # Fetch and save all IARC info.
            refresh_iarc_ratings([app.id])

            # Flag for rereview if it changed to adult.
            ratings_body = row.get('rating_system')
            rating = RATINGS[ratings_body.id].get(row['new_rating'])
            _flag_rereview_adult(app, ratings_body, rating)

            # Log change reason.
            reason = row.get('change_reason')
            amo.log(amo.LOG.CONTENT_RATING_CHANGED, app,
                    details={'comments': '%s:%s, %s' %
                             (ratings_body.name, rating.name, reason)})

        except Exception as e:
            # Any exceptions we catch, log, and keep going.
            log.debug('Exception: %s' % e)
            continue


def _flag_rereview_adult(app, ratings_body, rating):
    """Flag app for rereview if it receives an Adult content rating."""
    old_rating = app.content_ratings.filter(ratings_body=ratings_body.id)
    if not old_rating.exists():
        return

    if rating.adult and not old_rating[0].get_rating().adult:
        RereviewQueue.flag(
            app, amo.LOG.CONTENT_RATING_TO_ADULT,
            message=_('Content rating changed to Adult.'))
