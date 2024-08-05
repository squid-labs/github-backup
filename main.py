import os
import shutil
import tempfile
import zipfile
import logging
import sys
import requests
import time
import configparser
import errno
import stat

from backup import (
    backup_account,
    backup_repositories,
    check_git_lfs_install,
    filter_repositories,
    get_authenticated_user,
    logger,
    mkdir_p,
    parse_args,
    retrieve_repositories,
)

def main():
    try:
        # set timestamp for file
        timestr = time.strftime("%Y%m%d-%H%M%S")

        # configure parser to read config
        configParser = configparser.ConfigParser()
        configParser.sections()
        configParser.read('config.ini')

        # retrieving value from config file
        archive_output_directory=configParser['DEFAULT']['ARCHIVE_OUTPUT_DIRECTORY']
        log_output_directory=configParser['DEFAULT']['LOG_OUTPUT_DIRECTORY']
        github_backup_filename = configParser['DEFAULT']['GITHUB_BACKUP_FILENAME']
        github_output_directory=configParser['DEFAULT']['GITHUB_OUTPUT_DIRECTORY']
        github_username= configParser['DEFAULT']['GITHUB_USERNAME']
        github_token_list=configParser['DEFAULT']['GITHUB_TOKEN'].split(',')
        length = len(github_token_list)

        # temporary output directory
        output_directory = os.path.realpath(github_output_directory) + '\\' + timestr

        # creating temporary folder for github output directory
        if not os.path.isdir(output_directory):
            logger.info("Create output directory {0}".format(output_directory))
            mkdir_p(output_directory)

        # creating temporary folder for archive output directory
        if not os.path.isdir(archive_output_directory):
            logger.info("Create output directory {0}".format(archive_output_directory))
            mkdir_p(archive_output_directory)

        # creating temporary folder for log output directory
        if not os.path.isdir(log_output_directory):
            logger.info("Create output directory {0}".format(log_output_directory))
            mkdir_p(log_output_directory)
        
        # creating log file
        log_file = log_output_directory + '\\logs-' + timestr + '.log'
        with open(log_file, 'w') as f: 
            f.write('Starting log file.') 

        logging.basicConfig(
            filename=log_file, 
            filemode="w",
            format="%(asctime)s.%(msecs)03d: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
            level=logging.INFO,
        )

        for i in range(length):
            # defining arguments to pass to backup.py
            args = parse_args([github_username, '-f', github_token_list[i], '-i','--repositories', '-O', '--organization', '-P', '--private'])   
    
            if args.lfs_clone:
                check_git_lfs_install()

            if not args.as_app:
                logger.info('Backing up account {0} to {1}'.format(args.user, output_directory))
                authenticated_user = get_authenticated_user(args)
            else:
                authenticated_user = {"login": None}

            repositories = retrieve_repositories(args, authenticated_user)
            repositories = filter_repositories(args, repositories)
            backup_repositories(args, output_directory, repositories)
            backup_account(args, output_directory)

        logger.info('Backing up completed')
        
        # Create a zip file of the backup
        filename = github_backup_filename + '-' + timestr + '.zip'
        zip_file_path = os.path.join(output_directory, filename)
        logger.info(zip_file_path)
        with zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, _, files in os.walk(output_directory + '\\repositories'):
                for file in files:
                    zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), output_directory))
        logger.info('File compressed process completed')

        # move the file to archive
        logger.info('File moving to archived folder')
        shutil.move(output_directory + '\\' + filename , archive_output_directory + filename)
        
        # move file
        logger.info(github_output_directory + ' to be deleted')
        rmtree(github_output_directory)

    except Exception as e:
        # Display an error message.
        logger.error(str(e))

def rmtree(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            filename = os.path.join(root, name)
            os.chmod(filename, stat.S_IWUSR)
            os.remove(filename)
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)

# Test locally
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)