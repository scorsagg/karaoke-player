import os
import subprocess

from PySide6.QtCore import QTimer
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox

from source_code.workers.process_thread import ProcessThread


class ProcessingController:
    """FFmpeg-oriented processing orchestration extracted from the main window.

    This keeps the app shell focused on UI/bootstrap responsibilities while the
    command families and task lifecycle stay in a dedicated controller.
    """

    def build_amplify_export_cmd(self, app, input_file, output_file, factor, media_kind, src_ext):
        """Build FFmpeg command to amplify audio or video and preserve the appropriate container."""
        ffmpeg_path = app.settings["ffmpeg_path"]
        try:
            factor_value = float(factor)
        except Exception:
            factor_value = 1.0

        if factor_value > 1.0:
            volume_filter = f"volume={factor_value:.4f},alimiter=limit=0.98:attack=5:release=50"
        else:
            volume_filter = f"volume={factor_value:.4f}"

        if media_kind == "video":
            return [
                ffmpeg_path, "-y", "-i", input_file,
                "-af", volume_filter,
                "-c:v", "copy",
                "-c:a", "aac", "-b:a", "192k",
                output_file,
            ]

        if src_ext == "wav":
            return [ffmpeg_path, "-y", "-i", input_file, "-af", volume_filter, "-c:a", "pcm_s16le", "-ar", "44100", output_file]
        if src_ext == "mp3":
            return [ffmpeg_path, "-y", "-i", input_file, "-af", volume_filter, "-c:a", "libmp3lame", "-b:a", "320k", output_file]
        if src_ext in {"aac", "m4a"}:
            return [ffmpeg_path, "-y", "-i", input_file, "-af", volume_filter, "-c:a", "aac", "-b:a", "192k", output_file]
        if src_ext in {"flac", "ogg", "opus"}:
            codec = {"flac": "flac", "ogg": "libvorbis", "opus": "libopus"}[src_ext]
            bitrate = "192k" if src_ext != "flac" else None
            cmd = [ffmpeg_path, "-y", "-i", input_file, "-af", volume_filter, "-c:a", codec]
            if bitrate:
                cmd += ["-b:a", bitrate]
            cmd += [output_file]
            return cmd

        return [ffmpeg_path, "-y", "-i", input_file, "-af", volume_filter, "-c:a", "aac", "-b:a", "192k", output_file]

    def build_format_conversion_cmd(self, app, input_file, output_file, target_fmt, bitrate):
        """Build FFmpeg command for format conversion (Feature 7)."""
        ffmpeg_path = app.settings["ffmpeg_path"]

        if target_fmt in ["mp3", "wav", "aac", "m4a"]:
            if target_fmt == "mp3":
                return [ffmpeg_path, "-y", "-i", input_file, "-vn", "-acodec", "libmp3lame", "-b:a", bitrate, output_file]
            if target_fmt == "wav":
                return [ffmpeg_path, "-y", "-i", input_file, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", output_file]
            if target_fmt == "aac":
                return [ffmpeg_path, "-y", "-i", input_file, "-vn", "-acodec", "aac", "-b:a", bitrate, output_file]
            if target_fmt == "m4a":
                return [ffmpeg_path, "-y", "-i", input_file, "-vn", "-acodec", "aac", "-b:a", bitrate, output_file]

        if target_fmt in ["mp4", "mkv"]:
            if target_fmt == "mp4":
                return [ffmpeg_path, "-y", "-i", input_file, "-c:v", "libx264", "-preset", "fast", "-acodec", "aac", "-b:a", bitrate, output_file]
            if target_fmt == "mkv":
                return [ffmpeg_path, "-y", "-i", input_file, "-c:v", "copy", "-acodec", "aac", "-b:a", bitrate, output_file]

        return [ffmpeg_path, "-y", "-i", input_file, "-c", "copy", output_file]

    def build_audio_multi_trim_cmd(self, app, input_file, output_file, target_fmt, ranges_ms):
        """Build FFmpeg command to keep multiple audio ranges and concatenate them."""
        ffmpeg_path = app.settings["ffmpeg_path"]

        parts = []
        for i, (s_ms, e_ms) in enumerate(ranges_ms):
            s = s_ms / 1000.0
            e = e_ms / 1000.0
            parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}]")

        a_inputs = "".join([f"[a{i}]" for i in range(len(ranges_ms))])
        parts.append(f"{a_inputs}concat=n={len(ranges_ms)}:v=0:a=1[a]")
        filter_complex = ";".join(parts)

        cmd = [ffmpeg_path, "-y", "-i", input_file, "-filter_complex", filter_complex, "-map", "[a]"]

        if target_fmt == "mp3":
            cmd += ["-acodec", "libmp3lame", "-b:a", "192k", output_file]
        elif target_fmt == "wav":
            cmd += ["-acodec", "pcm_s16le", "-ar", "44100", output_file]
        elif target_fmt == "aac":
            cmd += ["-acodec", "aac", "-b:a", "192k", output_file]
        elif target_fmt == "m4a":
            cmd += ["-acodec", "aac", "-b:a", "192k", output_file]
        else:
            cmd += ["-acodec", "copy", output_file]

        return cmd

    def build_video_multi_trim_cmd(self, app, input_file, output_file, target_fmt, ranges_ms):
        """Build FFmpeg command to keep multiple video ranges and concatenate them."""
        ffmpeg_path = app.settings["ffmpeg_path"]

        parts = []
        for i, (s_ms, e_ms) in enumerate(ranges_ms):
            s = s_ms / 1000.0
            e = e_ms / 1000.0
            parts.append(f"[0:v]trim=start={s}:end={e},setpts=PTS-STARTPTS[v{i}]")
            parts.append(f"[0:a]atrim=start={s}:end={e},asetpts=PTS-STARTPTS[a{i}]")

        va_inputs = "".join([f"[v{i}][a{i}]" for i in range(len(ranges_ms))])
        parts.append(f"{va_inputs}concat=n={len(ranges_ms)}:v=1:a=1[v][a]")
        filter_complex = ";".join(parts)

        cmd = [ffmpeg_path, "-y", "-i", input_file, "-filter_complex", filter_complex, "-map", "[v]", "-map", "[a]"]

        if target_fmt == "mp4":
            cmd += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", output_file]
        elif target_fmt == "mkv":
            cmd += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", output_file]
        elif target_fmt == "webm":
            cmd += ["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus", "-b:a", "192k", output_file]
        elif target_fmt == "avi":
            cmd += ["-c:v", "mpeg4", "-q:v", "5", "-c:a", "libmp3lame", "-b:a", "192k", output_file]
        else:
            cmd += ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-b:a", "192k", output_file]

        return cmd

    def _build_join_merge_cmd(self, app, input_a, input_b, mode, out_path):
        """Build ffmpeg command for merge/join operations."""
        ffmpeg = app.settings["ffmpeg_path"]
        out_ext = os.path.splitext(out_path)[1].lower()

        if mode == "video_audio_merge":
            a_type = app._classify_media_type_for_merge(input_a)
            b_type = app._classify_media_type_for_merge(input_b)
            if a_type == "video" and b_type == "audio":
                video_input = input_a
                audio_input = input_b
            elif a_type == "audio" and b_type == "video":
                video_input = input_b
                audio_input = input_a
            else:
                raise RuntimeError(
                    f"video_audio_merge expected one video + one audio, got a_type={a_type}, b_type={b_type}"
                )

            if os.path.normcase(os.path.abspath(video_input)) == os.path.normcase(os.path.abspath(audio_input)):
                raise RuntimeError("Invalid video+audio merge pairing: video and audio inputs resolved to the same file")

            behavior = app._resolve_merge_behavior(mode)

            if behavior == "append":
                try:
                    vdur = float(app.get_video_duration_via_ffprobe(video_input))
                except Exception:
                    vdur = 0.0
                if vdur <= 0:
                    vdur = 1.0

                try:
                    adur = float(app.get_video_duration_via_ffprobe(audio_input))
                except Exception:
                    adur = 0.0
                if adur <= 0:
                    adur = 1.0

                return [
                    ffmpeg,
                    "-y",
                    "-i",
                    video_input,
                    "-i",
                    audio_input,
                    "-filter_complex",
                    f"[0:v]setpts=PTS-STARTPTS,tpad=stop_mode=clone:stop_duration={adur:.3f}[v];"
                    f"anullsrc=channel_layout=stereo:sample_rate=44100:d={vdur:.3f}[sil];"
                    "[1:a]aresample=44100,asetpts=PTS-STARTPTS[a1];"
                    "[sil][a1]concat=n=2:v=0:a=1[a]",
                    "-map",
                    "[v]",
                    "-map",
                    "[a]",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "fast",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    out_path,
                ]

            offset_s = 0.0
            try:
                offset_s = max(0.0, float(app.merge_audio_offset_spin.value()))
            except Exception:
                offset_s = 0.0

            if offset_s > 0.0:
                delay_ms = int(round(offset_s * 1000.0))
                cmd = [
                    ffmpeg,
                    "-y",
                    "-i",
                    video_input,
                    "-i",
                    audio_input,
                    "-filter_complex",
                    f"[1:a]adelay={delay_ms}:all=1,aresample=44100,asetpts=PTS-STARTPTS[a]",
                    "-map",
                    "0:v:0",
                    "-map",
                    "[a]",
                    "-c:v",
                    "copy",
                    "-shortest",
                    "-sn",
                    "-dn",
                ]
            else:
                cmd = [
                    ffmpeg,
                    "-y",
                    "-i",
                    video_input,
                    "-i",
                    audio_input,
                    "-map",
                    "0:v:0",
                    "-map",
                    "1:a:0",
                    "-c:v",
                    "copy",
                    "-shortest",
                    "-sn",
                    "-dn",
                ]

            if out_ext == ".mkv":
                cmd += ["-c:a", "aac", "-b:a", "192k", out_path]
            else:
                cmd += ["-c:a", "aac", "-b:a", "192k", out_path]
            return cmd

        if mode == "audio_audio_join":
            behavior = app._resolve_merge_behavior(mode)
            if behavior == "overlay":
                cmd = [
                    ffmpeg,
                    "-y",
                    "-i",
                    input_a,
                    "-i",
                    input_b,
                    "-filter_complex",
                    "[0:a]aresample=44100,asetpts=PTS-STARTPTS[a0];[1:a]aresample=44100,asetpts=PTS-STARTPTS[a1];[a0][a1]amix=inputs=2:duration=longest:dropout_transition=2[a]",
                    "-map",
                    "[a]",
                ]
            else:
                cmd = [
                    ffmpeg,
                    "-y",
                    "-i",
                    input_a,
                    "-i",
                    input_b,
                    "-filter_complex",
                    "[0:a]aresample=44100,asetpts=PTS-STARTPTS[a0];[1:a]aresample=44100,asetpts=PTS-STARTPTS[a1];[a0][a1]concat=n=2:v=0:a=1[a]",
                    "-map",
                    "[a]",
                ]
            if out_ext == ".mp3":
                cmd += ["-c:a", "libmp3lame", "-b:a", "320k", out_path]
            else:
                cmd += ["-c:a", "pcm_s16le", "-ar", "44100", out_path]
            return cmd

        behavior = app._resolve_merge_behavior(mode)
        if behavior == "overlay":
            return [
                ffmpeg,
                "-y",
                "-i",
                input_a,
                "-i",
                input_b,
                "-filter_complex",
                "[0:v]fps=30,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v0];"
                "[1:v]fps=30,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v1];"
                "[v0][v1]blend=all_mode='screen':all_opacity=0.5[v];"
                "[0:a]aresample=44100[a0];[1:a]aresample=44100[a1];[a0][a1]amix=inputs=2:duration=shortest:dropout_transition=2[a]",
                "-map",
                "[v]",
                "-map",
                "[a]",
                "-shortest",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                out_path,
            ]

        return [
            ffmpeg,
            "-y",
            "-i",
            input_a,
            "-i",
            input_b,
            "-filter_complex",
            "[0:v]fps=30,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p,setpts=PTS-STARTPTS[v0];"
            "[1:v]fps=30,scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720:(ow-iw)/2:(oh-ih)/2,format=yuv420p,setpts=PTS-STARTPTS[v1];"
            "[0:a]aresample=44100,asetpts=PTS-STARTPTS[a0];"
            "[1:a]aresample=44100,asetpts=PTS-STARTPTS[a1];"
            "[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
            "-map",
            "[v]",
            "-map",
            "[a]",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            out_path,
        ]

    def launch_async_task(self, app, cmd, out_path, task_key, override_duration=0):
        self.kill_allocated_task(app, task_key)

        app.log_debug(
            f"[{task_key}] launch | output={out_path} | duration_hint={override_duration} | cmd={' '.join(map(str, cmd))}"
        )

        thread = ProcessThread(cmd, override_duration)
        app.active_tasks[task_key] = thread

        thread.status_update.connect(lambda text: app.export_splash.set_progress(app.export_splash.pbar.value(), text))
        thread.status_update.connect(lambda text: app.log_debug(f"[{task_key}] status | {text}"))
        thread.progress.connect(lambda v: app.export_splash.set_progress(v, app.export_splash.showMessageLabel.text()))
        thread.line_output.connect(lambda line: app.log_debug(f"[{task_key}] output | {line}"))
        thread.finished.connect(lambda success: self.handle_task_completion(app, task_key, out_path, success))
        thread.start()

    def kill_allocated_task(self, app, task_key):
        if task_key in app.active_tasks:
            thread = app.active_tasks.pop(task_key)
            was_running = False
            try:
                was_running = thread.isRunning()
            except Exception:
                pass
            app.log_debug(f"[{task_key}] cancel requested | running={was_running}")
            try:
                thread.stop()
            except Exception:
                pass
            try:
                waited = thread.wait(2000)
                app.log_debug(f"[{task_key}] cancel wait complete | stopped={waited}")
            except Exception:
                app.log_debug(f"[{task_key}] cancel wait raised exception")
            if app.export_splash:
                app.export_splash.close()
                app.export_splash = None
            app.status_label.setText("Status: Ready")

    def stop_all_tasks(self, app):
        """Stop all active tasks during app shutdown."""
        app.log_debug(f"[tasks] stop_all_tasks | active_count={len(app.active_tasks)}")
        for task_key in list(app.active_tasks.keys()):
            try:
                thread = app.active_tasks[task_key]
                thread.stop()
                waited = thread.wait(1000)
                app.log_debug(f"[{task_key}] shutdown stop | stopped={waited}")
            except Exception:
                app.log_debug(f"[{task_key}] shutdown stop | exception while stopping")
        app.active_tasks.clear()

    def handle_task_completion(self, app, task_key, out_path, success):
        app.active_tasks.pop(task_key, None)

        app.log_debug(
            f"[{task_key}] completion | success={success} | out_path={out_path} | "
            f"exists={bool(out_path and os.path.exists(out_path))}"
        )

        if app.export_splash:
            app.export_splash.close()
            app.export_splash = None

        app.status_label.setText("Status: Ready")

        if not success:
            if task_key == "merge_task" and getattr(app, "_last_merge_cmd_text", ""):
                try:
                    QApplication.clipboard().setText(app._last_merge_cmd_text)
                except Exception:
                    pass
                QMessageBox.warning(
                    app,
                    "Processing Break",
                    "Execution pipeline stopped or configuration error checked.\n\n"
                    "Final ffmpeg command has been copied to clipboard for debugging.",
                )
                return
            QMessageBox.warning(app, "Processing Break", "Execution pipeline stopped or configuration error checked.")
            return

        if out_path and os.path.exists(out_path):
            is_audio_task = task_key in ["extract_task", "trim_task", "convert_task"]
            if task_key == "amplify_task":
                is_audio_task = getattr(app, '_current_export_media_kind', 'audio') == 'audio'
            if task_key == "merge_task":
                is_audio_task = app.classify_media_type(out_path) == "audio"
            app.load_video(out_path, is_audio_only=is_audio_task)

            if task_key == "extract_task":
                app.audio_tools_file_path = out_path
                extracted_name = os.path.basename(out_path)
                app.audio_file_status.setText(f"✅ {extracted_name} (Extracted Audio)")
                app.update_extraction_ui(False)

            if task_key in ["trim_task", "convert_task", "amplify_task"]:
                app.audio_tools_file_path = out_path
                output_name = os.path.basename(out_path)
                app.audio_file_status.setText(f"✅ {output_name} (Processed Audio)")

            if task_key == "merge_task":
                output_name = os.path.basename(out_path)
                media_kind = app.classify_media_type(out_path)
                app.merge_status_label.setText(f"✅ Merge completed: {output_name}")
                if media_kind == "audio":
                    app.audio_tools_file_path = out_path
                    app.audio_file_status.setText(f"✅ {output_name} (Merged Output)")

            if task_key == "amplify_task":
                app.amp_status_label.setText(f"✅ Amplified file loaded: {os.path.basename(out_path)}")
                app._reset_export_amplify_factor(os.path.basename(out_path))

            QMessageBox.information(app, "Success", f"Output loaded successfully:\n{os.path.basename(out_path)}")

            if task_key in ["extract_task", "trim_task"]:
                QTimer.singleShot(100, lambda: app.handle_navigation_change(app.PAGE_AUDIO_STUDIO))
            if task_key in ["convert_task", "normalize_task"]:
                QTimer.singleShot(100, lambda: app.handle_navigation_change(app.PAGE_CONVERT_EXPORT))
            if task_key == "amplify_task":
                QTimer.singleShot(100, app._return_to_amplify_export_tab)
            if task_key == "merge_task":
                QTimer.singleShot(100, lambda: app.handle_navigation_change(app.PAGE_CONVERT_EXPORT))

            if task_key == "widen_task":
                QTimer.singleShot(100, app._return_to_widen_video_tab)
