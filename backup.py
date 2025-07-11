"""
Backup and Recovery System
Automated database backup and restore functionality
"""

import os
import sqlite3
import shutil
import gzip
import json
from datetime import datetime, timedelta
import schedule
import threading
import time
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class BackupManager:
    """Handles automated backup and recovery operations"""
    
    def __init__(self, app=None):
        self.app = app
        self.backup_path = None
        self.db_path = None
        self.retention_days = 30
        
    def init_app(self, app):
        """Initialize backup manager with Flask app"""
        self.app = app
        self.backup_path = app.config.get('BACKUP_PATH', 'backups')
        self.retention_days = app.config.get('BACKUP_RETENTION_DAYS', 30)
        
        # Get database path from config
        db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
        if db_uri.startswith('sqlite:///'):
            self.db_path = db_uri.replace('sqlite:///', '')
        
        # Create backup directory
        Path(self.backup_path).mkdir(parents=True, exist_ok=True)
        
        # Schedule automatic backups
        self.schedule_backups()
        
    def schedule_backups(self):
        """Schedule automatic backups"""
        # Schedule daily backup at 2 AM
        schedule.every().day.at("02:00").do(self.create_backup)
        
        # Schedule weekly full backup on Sunday at 3 AM
        schedule.every().sunday.at("03:00").do(self.create_full_backup)
        
        # Start scheduler in background thread
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
                
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
    def create_backup(self, backup_type='daily'):
        """Create database backup"""
        try:
            if not self.db_path or not os.path.exists(self.db_path):
                logger.error("Database file not found for backup")
                return False
                
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"backup_{backup_type}_{timestamp}.db.gz"
            backup_filepath = os.path.join(self.backup_path, backup_filename)
            
            # Create compressed backup
            with open(self.db_path, 'rb') as f_in:
                with gzip.open(backup_filepath, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            # Create metadata file
            metadata = {
                'timestamp': timestamp,
                'backup_type': backup_type,
                'original_size': os.path.getsize(self.db_path),
                'compressed_size': os.path.getsize(backup_filepath),
                'database_version': self.get_database_version()
            }
            
            metadata_file = backup_filepath.replace('.db.gz', '_metadata.json')
            with open(metadata_file, 'w') as f:
                json.dump(metadata, f, indent=2)
                
            logger.info(f"Backup created: {backup_filename}")
            
            # Clean old backups
            self.cleanup_old_backups()
            
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            return False
            
    def create_full_backup(self):
        """Create full system backup including uploads"""
        try:
            # Create database backup
            db_backup_success = self.create_backup('full')
            
            if not db_backup_success:
                return False
                
            # Backup upload files
            upload_folder = self.app.config.get('UPLOAD_FOLDER', 'static/uploads')
            if os.path.exists(upload_folder):
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                uploads_backup = os.path.join(self.backup_path, f"uploads_backup_{timestamp}.tar.gz")
                
                import tarfile
                with tarfile.open(uploads_backup, "w:gz") as tar:
                    tar.add(upload_folder, arcname="uploads")
                    
                logger.info(f"Full backup completed with uploads: {uploads_backup}")
                
            return True
            
        except Exception as e:
            logger.error(f"Full backup failed: {str(e)}")
            return False
            
    def restore_backup(self, backup_filename):
        """Restore database from backup"""
        try:
            backup_filepath = os.path.join(self.backup_path, backup_filename)
            
            if not os.path.exists(backup_filepath):
                logger.error(f"Backup file not found: {backup_filename}")
                return False
                
            # Create backup of current database
            current_backup = f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            shutil.copy2(self.db_path, os.path.join(self.backup_path, current_backup))
            
            # Restore from compressed backup
            with gzip.open(backup_filepath, 'rb') as f_in:
                with open(self.db_path, 'wb') as f_out:
                    shutil.copyfileobj(f_in, f_out)
                    
            logger.info(f"Database restored from: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring database: {str(e)}")
            return False
            
# Global backup manager instance
backup_manager = BackupManager()
