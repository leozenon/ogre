#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import with_statement
__license__   = 'GPL v3'
__docformat__ = 'restructuredtext en'


# Released under the terms of the GNU General Public Licence, version 3
# <http://www.gnu.org/licenses/>
#
# Requires Calibre version 0.7.55 or higher.
#
# All credit given to i♥cabbages and The Dark Reverser for the original standalone scripts.
# We had the much easier job of converting them to a calibre plugin.
#
# This plugin is meant to decrypt eReader PDBs, Adobe Adept ePubs, Barnes & Noble ePubs,
# Adobe Adept PDFs, Amazon Kindle and Mobipocket files without having to
# install any dependencies... other than having calibre installed, of course.
#
# Configuration:
# Check out the plugin's configuration settings by clicking the "Customize plugin"
# button when you have the "DeDRM" plugin highlighted (under Preferences->
# Plugins->File type plugins). Once you have the configuration dialog open, you'll
# see a Help link on the top right-hand side.
#
# Revision history:
#   6.0.0 - Initial release
#   6.0.1 - Bug Fixes for Windows App, Kindle for Mac and Windows Adobe Digital Editions
#   6.0.2 - Restored call to Wine to get Kindle for PC keys, added for ADE
#   6.0.3 - Fixes for Kindle for Mac and Windows non-ascii user names
#   6.0.4 - Fixes for stand-alone scripts and applications
#           and pdb files in plugin and initial conversion of prefs.
#   6.0.6 - Fix up an incorrect function call

"""
Decrypt DRMed ebooks.
"""

PLUGIN_NAME = u"DeDRM"
PLUGIN_VERSION_TUPLE = (6, 0, 7)
PLUGIN_VERSION = u".".join([unicode(str(x)) for x in PLUGIN_VERSION_TUPLE])
