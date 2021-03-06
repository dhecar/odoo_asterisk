from datetime import datetime, timedelta
import humanize
import logging
from openerp import models, fields, api, _
from openerp import sql_db
import requests
from urlparse import urljoin


logger = logging.getLogger(__name__)

DISPOSITION_TYPES = (
    ('NO ANSWER', 'No answer'),
    ('FAILED', 'Failed'),
    ('BUSY', 'Busy'),
    ('ANSWERED', 'Answered'),
    ('CONGESTION', 'Congestion'),
)



class Cdr(models.Model):
    _name = 'asterisk.cdr'
    _description = 'Call Detail Record'
    _order = 'started desc'

    accountcode = fields.Char(size=20, string='Account code', index=True)
    src = fields.Char(size=80, string='Src', index=True)
    dst = fields.Char(size=80, string='Dst', index=True)
    dcontext = fields.Char(size=80, string='Dcontext')
    clid = fields.Char(size=80, string='Clid', index=True)
    channel = fields.Char(size=80, string='Channel', index=True)
    dstchannel = fields.Char(size=80, string='Dst channel', index=True)
    lastapp = fields.Char(size=80, string='Last app')
    lastdata = fields.Char(size=80, string='Last data')
    started = fields.Datetime(index=True, oldname='start')
    answered = fields.Datetime(index=True, oldname='answer')
    ended = fields.Datetime(index=True, oldname='end')
    duration = fields.Integer(string='Duration', index=True)
    billsec = fields.Integer(string='Billsec', index=True)
    disposition = fields.Char(size=45, string='Disposition', index=True)
    amaflags = fields.Integer(string='AMA flags')
    userfield = fields.Char(size=255, string='Userfield')
    uniqueid = fields.Char(size=150, string='Uniqueid', index=True)
    peeraccount = fields.Char(size=20, string='Peer account', index=True)
    linkedid = fields.Char(size=150, string='Linked id')
    sequence = fields.Integer(string='Sequence')
    recording_filename = fields.Char()
    recording_widget = fields.Char(compute='_get_recording_widget')
    recording_download = fields.Char(compute='_get_recording_download')
    # QoS
    ssrc = fields.Char(string='Our SSRC')
    themssrc = fields.Char(string='Other SSRC')
    lp = fields.Integer(string='Local Lost Packets')
    rlp = fields.Integer(string='Remote Lost Packets')
    rxjitter = fields.Float(string='RX Jitter')
    txjitter = fields.Float(string='TX Jitter')
    rxcount = fields.Integer(string='RX Count')
    txcount = fields.Integer(string='TX Count')
    rtt = fields.Float(string='Round Trip Time')


    @api.model
    def grant_asterisk_access(self):
        cr = sql_db.db_connect(self.env.cr.dbname).cursor()
        sql = "GRANT ALL on asterisk_cdr to asterisk"
        cr.execute(sql)
        sql = "GRANT ALL on asterisk_cdr_id_seq to asterisk"
        cr.execute(sql)
        cr.commit()
        cr.close()


    @api.multi
    def _get_recording_widget(self):
        for rec in self:
            rec.recording_widget = '<audio id="sound_file" preload="auto" ' \
                    'controls="controls"> ' \
                    '<source src="/recording/{}" type="audio/wav"/>'.format(
                                                        rec.recording_filename)


    @api.multi
    def _get_recording_download(self):
        for rec in self:
            rec.recording_download = '<a href="/recording/{}">Download</a>'.format(
                rec.recording_filename)


    @api.model
    def log_qos(self, values):
        logger.debug(values)
        uniqueid = values.get('uniqueid')
        linkedid = values.get('linkedid')
        cdrs = self.env['asterisk.cdr'].search([
            ('uniqueid', '=', uniqueid),
            ('linkedid', '=', linkedid),
            ('end', '>', (datetime.now() - timedelta(seconds=10)).strftime(
                '%Y-%m-%d %H:%M:%S')
            ),
        ])
        if not cdrs:
            logger.warning('Omitting QoS, CDR not found!')
            return False
        else:
            logger.debug('Found CDR for QoS.')
            cdr = cdrs[0]
            cdr.ssrc =values.get('ssrc')
            cdr.themssrc = values.get('themssrc')
            cdr.lp = int(values.get('lp'))
            cdr.rlp = int(values.get('rlp'))
            cdr.rxjitter = float(values.get('rxjitter'))
            cdr.txjitter = float(values.get('txjitter'))
            cdr.rxcount = int(values.get('rxcount'))
            cdr.txcount = int(values.get('txcount'))
            cdr.rtt = float(values.get('rtt'))
            return True
