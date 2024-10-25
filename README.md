Introduction
============

This script is meant to get you started with OpenUpgrade as hassle free as possible, allowing you to evaluate OpenUpgrade without much upfront investment of time or resources.

Getting Started
---------------

Any unix like system that has python and docker should be able to run this. You will need to backup your current database with Odoo's database manager in the zip format (or pass the url of your Odoo instance and provide the database admin password) and a lot of free disk space. Expect the migration process to take hours for a reasonably big database, and multiply with the amount of versions to want to migrate through.

Run

```shell
# doesn't matter where you put this,
# just should be empty and writable
mkdir -p /var/tmp/openupgrade
cd /var/tmp/openupgrade
wget -q https://hbrunn.github.io/OpenUpgrade/run-migration.py
env python3 run-migration.py https://your-odoo-installation.tld
# (or pass a backup in zip format you downloaded from your database manager)
```

You can also [download](https://hbrunn.github.io/OpenUpgrade/run-migration.py) the script and run it locally.

This will do the following things:

- extract version information from the backup to know which version(s) of OpenUpgrade to download
- set up a docker configuration for every version
- extract your backup into the work directory in ./source
- run OpenUpgrade on this to migrate to the latest supported version
- export a backup of the migrated database you can restore in your new Odoo instance

OCA addons
----------

If you use addons from OCA, they should be detected automatically and the appropriate repositories added to the migration sources. You can pass the list of repositories manually with the `--repos` parameter, like `--repos account-financial-tools server-tools web`, in case you want to override the autodetection.

Solving problems
----------------

In case the process fails at a point, you'll usually need to have an expert look into your data and possibly custom code. There are however some common gotchas:

- take care that you use the latest code of Odoo for your current version and update your database
- update your database anyways to recreate provisioned records (like record rules, the admin employee, ...) that users tend to delete instead of deactivate, which breaks the migration

Customization
-------------

The script creates a subfolder in ./docker for every version of OpenUpgrade it runs. If you need extra requirements or repositories, create a file _extra\_repos.yml_ and/or _extra\_requirements.txt_ there to add additional Odoo repositories and python requirements. Then rerun the script, it will rebuild the containers and restart the migration.

Test migration in development
-----------------------------

If you want to help testing the current development version of OpenUpgrade, first migrate your database to the latest fully supported version using the above if you're not on that version already, and test it thoroughly. Backup this database and use this backup for the following command.

Run the script as above (you might want to checkout the repository so you don't have to redownload it all the time), but add `--experimental`

```shell
    ./run-migration.py --experimental /wherever/you/put/the/odoo/backup.zip
```

this will apply all open PRs of the current experimental version (might fail if some PRs are mutually exclusive), and run the migration. Very likely this will fail, then you can inspect the logfiles in ./logs to see if this leads to useful(!) input you can give on the PR for the module whose migration fails. Note it's also quite possible that a module migration fails because the migration of some module before did something wrong, or is just missing altogether. Don't just dump a stack trace on github without further analysis, this is almost never helpful for anyone.

To be more specific with testing, you can pass PR numbers to the `--prs` parameter, as in `--experimental --prs 42 43 44`. This will only apply the listed PRs, allowing you to only test a subset of open PRs. It's your responsibility to select a combination of PRs that make sense, ie. if you want to test the unmerged `account` migration, you'll also have to add the PRs for `analytic`, `mail` and all other dependencies of the `account` module as far as they exist, recursively.

Don't forget to delete the src folder of the experimental version after each test to be sure to test with a clean version of the testable code.
