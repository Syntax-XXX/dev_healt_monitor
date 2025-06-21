import subprocess
import datetime
from collections import Counter
import sys
import threading

# Optional: GUI support
try:
    import tkinter as tk
    from tkinter import scrolledtext, messagebox
except ImportError:
    tk = None

# Optional: Native notifications
try:
    from plyer import notification
except ImportError:
    notification = None

# --- CONFIGURABLE SETTINGS ---
LONG_SESSION_HOURS = 3
LATE_NIGHT_START = 22  # 22:00
LATE_NIGHT_END = 6     # 06:00
MIN_BREAK_MINUTES = 5


def get_git_commit_times():
    """Return a list of commit datetime objects from git log."""
    try:
        result = subprocess.run(
            ["git", "log", "--pretty=format:%ct"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )
        timestamps = [int(line) for line in result.stdout.strip().split("\n") if line.strip()]
        return [datetime.datetime.fromtimestamp(ts) for ts in timestamps]
    except Exception as e:
        print(f"Error reading git log: {e}")
        return []

def analyze_sessions(commit_times):
    if not commit_times:
        print("No commit data found.")
        return
    commit_times = sorted(commit_times)
    sessions = []
    session = [commit_times[0]]
    for prev, curr in zip(commit_times, commit_times[1:]):
        diff = (curr - prev).total_seconds() / 60  # minutes
        if diff > MIN_BREAK_MINUTES:
            sessions.append(session)
            session = [curr]
        else:
            session.append(curr)
    if session:
        sessions.append(session)
    return sessions

def get_summary_text(sessions):
    lines = []
    lines.append("--- Developer Health Summary ---\n")
    long_sessions = [s for s in sessions if (s[-1] - s[0]).total_seconds() / 3600 > LONG_SESSION_HOURS]
    late_night_commits = [c for s in sessions for c in s if LATE_NIGHT_START <= c.hour or c.hour < LATE_NIGHT_END]
    lines.append(f"Total coding sessions: {len(sessions)}")
    lines.append(f"Long sessions (> {LONG_SESSION_HOURS}h): {len(long_sessions)}")
    lines.append(f"Late-night commits (22:00-06:00): {len(late_night_commits)}")
    if long_sessions:
        lines.append("\n⚠️  You had some long coding sessions. Remember to take breaks!")
    if late_night_commits:
        lines.append("\n⚠️  You committed code late at night. Prioritize rest for better productivity.")
    if not long_sessions and not late_night_commits:
        lines.append("\n✅ Your coding habits look healthy!")
    lines.append("\nAll analysis is local. Your data never leaves your machine.")
    return "\n".join(lines)

def show_native_notification(title, message):
    if notification is not None:
        notification.notify(title=title, message=message, timeout=8)

def print_summary(sessions):
    summary = get_summary_text(sessions)
    print(summary)
    # Show popup for both healthy and unhealthy patterns
    long_sessions = [s for s in sessions if (s[-1] - s[0]).total_seconds() / 3600 > LONG_SESSION_HOURS]
    late_night_commits = [c for s in sessions for c in s if LATE_NIGHT_START <= c.hour or c.hour < LATE_NIGHT_END]
    if long_sessions or late_night_commits:
        msg = ""
        if long_sessions:
            msg += f"You had {len(long_sessions)} long coding session(s). Remember to take breaks!\n"
        if late_night_commits:
            msg += f"You committed code late at night. Prioritize rest!"
        show_native_notification("Developer Health Alert", msg.strip())
    else:
        show_native_notification("Developer Health", "✅ Your coding habits look healthy!")

import time

def health_check_loop(show_popup_func, print_func=None, stop_event=None):
    # State for reminders and tracking
    last_break_reminder = None
    last_hydration_reminder = None
    last_activity_reminder = None
    last_ergonomics_tip = None
    last_mood_check = None
    daily_coding_minutes = 0
    weekly_coding_minutes = 0
    last_day = None
    last_week = None
    hydration_interval = 60  # minutes
    activity_interval = 90   # minutes
    mood_check_interval = 180 # minutes
    ergonomics_interval = 120 # minutes
    positive_reinforcement_given = False
    first_run = True
    
    while True:
        now = datetime.datetime.now()
        commit_times = get_git_commit_times()
        sessions = analyze_sessions(commit_times)
        if first_run:
            show_popup_func("Developer Health Monitor", "Monitoring started! You'll receive health notifications every 10 minutes.")
            first_run = False
        else:
            if sessions:
                summary = get_summary_text(sessions)
                if print_func:
                    print_func(summary)
                # Calculate daily/weekly coding time
                today = now.date()
                week = now.isocalendar()[1]
                if last_day != today:
                    daily_coding_minutes = 0
                    last_day = today
                    positive_reinforcement_given = False
                if last_week != week:
                    weekly_coding_minutes = 0
                    last_week = week
                # Add up today's and this week's coding minutes
                for s in sessions:
                    if s[0].date() == today:
                        daily_coding_minutes += int((s[-1] - s[0]).total_seconds() / 60)
                    if s[0].isocalendar()[1] == week:
                        weekly_coding_minutes += int((s[-1] - s[0]).total_seconds() / 60)
                # Break detection
                long_sessions = [s for s in sessions if (s[-1] - s[0]).total_seconds() / 3600 > LONG_SESSION_HOURS]
                no_break_sessions = [s for s in sessions if all((curr - prev).total_seconds() / 60 < 60 for prev, curr in zip(s, s[1:])) and (s[-1] - s[0]).total_seconds() / 3600 > 2]
                # Night owl
                late_night_commits = [c for s in sessions for c in s if LATE_NIGHT_START <= c.hour or c.hour < LATE_NIGHT_END]
                # Hydration/activity/ergonomics/mood reminders
                minutes_since_last_hydration = (now - last_hydration_reminder).total_seconds() / 60 if last_hydration_reminder else hydration_interval+1
                minutes_since_last_activity = (now - last_activity_reminder).total_seconds() / 60 if last_activity_reminder else activity_interval+1
                minutes_since_last_ergonomics = (now - last_ergonomics_tip).total_seconds() / 60 if last_ergonomics_tip else ergonomics_interval+1
                minutes_since_last_mood = (now - last_mood_check).total_seconds() / 60 if last_mood_check else mood_check_interval+1
                # Collect notifications
                notifications = []
                if long_sessions:
                    notifications.append(("Developer Health Alert", f"You had {len(long_sessions)} long coding session(s). Remember to take breaks!"))
                if no_break_sessions:
                    notifications.append(("Break Reminder", "You've been coding for over 2 hours without a significant break. Please take a break!"))
                if late_night_commits:
                    notifications.append(("Night Owl Alert", f"You committed code late at night. Prioritize rest for better productivity."))
                if daily_coding_minutes > 8*60:
                    notifications.append(("Work Limit Warning", "You've coded more than 8 hours today. Consider taking a longer break!"))
                if weekly_coding_minutes > 40*60:
                    notifications.append(("Weekly Limit Warning", "You've coded more than 40 hours this week. Watch for burnout!"))
                if minutes_since_last_hydration > hydration_interval:
                    notifications.append(("Hydration Reminder", "Time to drink some water!"))
                    last_hydration_reminder = now
                if minutes_since_last_activity > activity_interval:
                    notifications.append(("Activity Reminder", "Stand up and stretch for a few minutes!"))
                    last_activity_reminder = now
                if minutes_since_last_ergonomics > ergonomics_interval:
                    notifications.append(("Ergonomics Tip", "Check your posture and desk setup. 20-20-20 rule: every 20 minutes, look at something 20 feet away for 20 seconds."))
                    last_ergonomics_tip = now
                if minutes_since_last_mood > mood_check_interval:
                    notifications.append(("Mood Check-In", "How are you feeling? Take a moment to reflect on your mood and stress level."))
                    last_mood_check = now
                if not (long_sessions or no_break_sessions or late_night_commits or daily_coding_minutes > 8*60 or weekly_coding_minutes > 40*60):
                    if not positive_reinforcement_given:
                        notifications.append(("Great Job!", "✅ Your coding habits look healthy! Keep it up!"))
                        positive_reinforcement_given = True
                # Show notifications with 2s delay between each
                for title, msg in notifications:
                    show_popup_func(title, msg)
                    time.sleep(2)
            else:
                if print_func:
                    print_func("No commit data found.")
                show_popup_func("Developer Health Monitor", "No commit data found.")
        # Wait 10 minutes before next check
        for _ in range(600):
            if stop_event and stop_event.is_set():
                return
            time.sleep(1)

def main():
    health_check_loop(show_native_notification, print)

def run_gui(test_mode=False):
    if tk is None:
        print("tkinter is not available. Please install it or use the CLI mode.")
        sys.exit(1)
    window = tk.Tk()
    window.title("Developer Health Monitor")
    window.geometry("600x400")

    stop_event = threading.Event()

    def analyze_and_display():
        commit_times = get_git_commit_times()
        sessions = analyze_sessions(commit_times)
        if sessions:
            summary = get_summary_text(sessions)
            text_area.config(state='normal')
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, summary)
            text_area.config(state='disabled')
        else:
            messagebox.showinfo("No Data", "No commit data found.")

    def gui_show_popup(title, message):
        # Thread-safe popup in tkinter
        window.after(0, lambda: messagebox.showinfo(title, message))

    def on_close():
        stop_event.set()
        window.destroy()

    analyze_btn = tk.Button(window, text="Analyze Git Activity", command=analyze_and_display)
    analyze_btn.pack(pady=10)

    if test_mode:
        def test_popups_gui():
            notifications = [
                ("Developer Health Alert", "You had 2 long coding session(s). Remember to take breaks!"),
                ("Break Reminder", "You've been coding for over 2 hours without a significant break. Please take a break!"),
                ("Night Owl Alert", "You committed code late at night. Prioritize rest for better productivity."),
                ("Work Limit Warning", "You've coded more than 8 hours today. Consider taking a longer break!"),
                ("Weekly Limit Warning", "You've coded more than 40 hours this week. Watch for burnout!"),
                ("Hydration Reminder", "Time to drink some water!"),
                ("Activity Reminder", "Stand up and stretch for a few minutes!"),
                ("Ergonomics Tip", "Check your posture and desk setup. 20-20-20 rule: every 20 minutes, look at something 20 feet away for 20 seconds."),
                ("Mood Check-In", "How are you feeling? Take a moment to reflect on your mood and stress level."),
                ("Great Job!", "✅ Your coding habits look healthy! Keep it up!"),
            ]
            def show_all():
                for i, (title, msg) in enumerate(notifications):
                    window.after(i * 2000, lambda t=title, m=msg: messagebox.showinfo(t, m))
            show_all()
        test_btn = tk.Button(window, text="Test All Popups", command=test_popups_gui)
        test_btn.pack(pady=10)

    text_area = scrolledtext.ScrolledText(window, wrap=tk.WORD, width=70, height=20, state='disabled')
    text_area.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

    # Start periodic background check in a thread
    t = threading.Thread(target=health_check_loop, args=(gui_show_popup, None, stop_event), daemon=True)
    t.start()

    window.protocol("WM_DELETE_WINDOW", on_close)
    window.mainloop()

def cli_test():
    print("Developer Health Monitor CLI Test Mode")
    print("Type 'pup-1' to trigger all popups in sequence (2s interval). Type 'exit' to quit.")
    def test_popups():
        notifications = [
            ("Developer Health Alert", "You had 2 long coding session(s). Remember to take breaks!"),
            ("Break Reminder", "You've been coding for over 2 hours without a significant break. Please take a break!"),
            ("Night Owl Alert", "You committed code late at night. Prioritize rest for better productivity."),
            ("Work Limit Warning", "You've coded more than 8 hours today. Consider taking a longer break!"),
            ("Weekly Limit Warning", "You've coded more than 40 hours this week. Watch for burnout!"),
            ("Hydration Reminder", "Time to drink some water!"),
            ("Activity Reminder", "Stand up and stretch for a few minutes!"),
            ("Ergonomics Tip", "Check your posture and desk setup. 20-20-20 rule: every 20 minutes, look at something 20 feet away for 20 seconds."),
            ("Mood Check-In", "How are you feeling? Take a moment to reflect on your mood and stress level."),
            ("Great Job!", "✅ Your coding habits look healthy! Keep it up!"),
        ]
        for title, msg in notifications:
            show_native_notification(title, msg)
            time.sleep(2)
    while True:
        cmd = input("cli-test> ").strip()
        if cmd == "exit":
            break
        elif cmd == "pup-1":
            test_popups()
        else:
            print("Unknown command. Try 'pup-1' or 'exit'.")

if __name__ == "__main__":
    # Default: run GUI (for .exe or no args), unless --cli is specified
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        main()
    elif len(sys.argv) > 1 and sys.argv[1] == "--cli-test":
        cli_test()
    elif len(sys.argv) > 1 and sys.argv[1] == "--gui-test":
        run_gui(test_mode=True)
    else:
        run_gui()
