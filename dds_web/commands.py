import click
import flask

@click.command("monitor-usage")
@flask.cli.with_appcontext
def monitor_usage():
    """Check the units storage usage and compare with chosen quota."""

    # Email rescipient
    recipient: str = flask.current_app.config.get("MAIL_DDS")
    default_subject: str = "DDS: Usage quota warning!"

    # Imports
    # Own
    from dds_web.database import models
    
    # Run task
    for unit in models.Unit.query:
        flask.current_app.logger.debug(f"Unit: {unit}")

        # Get info from database
        quota: int = unit.quota
        warn_after: int = unit.warning_level
        current_usage: int = unit.size 

        flask.current_app.logger.debug(f"Quota: {quota}")
        flask.current_app.logger.debug(f"Warn after: {warn_after}")
        flask.current_app.logger.debug(f"Current usage: {current_usage}")

        # TODO: Check if 0 and then skip the next steps

        # Calculate usage in TB
        current_usage_tb = current_usage / 1e12 # 1 TB = 1 000 000 000 000

        flask.current_app.logger.debug(f"Current usage in TB: {current_usage_tb}")

        # Calculate percentage of quota
        perc_used = current_usage_tb / quota

        flask.current_app.logger.debug(f"Percentage used of quota: {perc_used}")

        # Email if the unit is using more 
        if perc_used > warn_after:
            # Email settings
            flask.current_app.logger.debug(f"The percentage is above the warning level: {perc_used}. ")