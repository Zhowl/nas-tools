# 定时更新themoviedb中正在上映的影片并下载预告让emby展示
import shutil
import sys
from datetime import datetime
import os
from subprocess import call

from tmdbv3api import TMDb, Movie

import log
import settings
from functions import get_dir_files_by_ext, get_dir_files_by_name, system_exec_command, is_chinese
from message.send import sendmsg

RUNING_FLAG = False


def run_hottrailers(refresh_flag=True):
    try:
        global RUNING_FLAG
        if RUNING_FLAG:
            log.error("【RUN】hottrailers任务正在执行中...")
        else:
            RUNING_FLAG = True
            hottrailers(refresh_flag)
            RUNING_FLAG = False
    except Exception as err:
        RUNING_FLAG = False
        log.error("【RUN】执行任务hottrailers出错：" + str(err))
        sendmsg("【NASTOOL】执行任务hottrailers出错！", str(err))


# 将预告目录中的预告片转移到电影目录，如果存在对应的电影了的话
def transfer_trailers(in_path):
    # 读取配置
    movie_path = settings.get("movie.movie_path")
    media_ext = settings.get("rmt.rmt_mediaext")
    movie_types = settings.get("rmt.rmt_movietype").split(",")
    trailer_file_list = get_dir_files_by_ext(in_path, media_ext)
    if len(trailer_file_list) == 0:
        log.info("【HOT-TRAILER】" + in_path + " 不存在预告片，删除目录...")
        shutil.rmtree(in_path, ignore_errors=True)
        return
    for trailer_file in trailer_file_list:
        if not os.path.exists(trailer_file):
            log.error("【HOT-TRAILER】" + trailer_file + " 原文件不存在，跳过...")
            continue
        trailer_file_dir = os.path.dirname(trailer_file)
        trailer_file_name = os.path.basename(trailer_file_dir)
        trailer_file_ext = os.path.splitext(trailer_file)[1]

        trailer_done = False
        for movie_type in movie_types:
            dest_path = os.path.join(movie_path, movie_type, trailer_file_name)
            if os.path.exists(dest_path):
                log.info("【HOT-TRAILER】" + trailer_file_name + " 进行转移...")
                dest_file_list = get_dir_files_by_ext(dest_path, media_ext)
                continue_flag = False
                for dest_movie_file in dest_file_list:
                    if dest_movie_file.find("-trailer.") != -1:
                        log.info("【HOT-TRAILER】预告片，跳过...")
                        continue_flag = True
                        break
                    trailer_dest_file = os.path.splitext(dest_movie_file)[0] + "-trailer" + trailer_file_ext
                    if os.path.exists(trailer_dest_file):
                        log.info("【HOT-TRAILER】" + trailer_dest_file + " 文件已存在，跳过...")
                        continue_flag = True
                        break
                    log.debug("【HOT-TRAILER】正在复制：" + trailer_file + " 到 " + trailer_dest_file)
                    # shutil.copy(trailer_file, trailer_dest_file)
                    call(["cp", trailer_file, trailer_dest_file])
                    log.info("【HOT-TRAILER】转移完成：" + trailer_dest_file)
                if continue_flag:
                    continue
                shutil.rmtree(trailer_file_dir, ignore_errors=True)
                log.info("【HOT-TRAILER】" + trailer_file_dir + "已删除！")
                trailer_done = True
        if not trailer_done:
            log.info("【HOT-TRAILER】" + trailer_file_name + " 不存在对应电影，跳过...")


def hottrailers(refresh_flag=True):
    # 读取配置
    youtube_dl_cmd = settings.get("youtobe.youtube_dl_cmd")
    hottrailer_total = int(settings.get("scheduler.hottrailer_total"))
    hottrailer_path = settings.get("movie.hottrailer_path")
    movie_path = settings.get("movie.movie_path")
    movie_types = settings.get("rmt.rmt_movietype").split(",")
    start_time = datetime.now()
    if refresh_flag:
        # 检索正在上映的电影
        tmdb = TMDb()
        tmdb.api_key = settings.get('rmt.rmt_tmdbkey')
        if not tmdb.api_key:
            log.error("【HOT-TRAILER】未配置rmt_tmdbkey，无法下载热门预告片！")
            return
        tmdb.language = 'zh-CN'
        tmdb.debug = True
        movie = Movie()

        # 正在上映与即将上映
        playing_list = []
        log.info("【HOT-TRAILER】检索正在上映电影...")
        page = 1
        now_playing = movie.now_playing(page)
        now_playing_total = 0
        while len(now_playing) > 0 and now_playing_total < hottrailer_total:
            now_playing_total = now_playing_total + len(now_playing)
            log.debug(">第 " + str(page) + " 页：" + str(now_playing_total))
            playing_list = playing_list + now_playing
            page = page + 1
            now_playing = movie.now_playing(page)
        log.info("【HOT-TRAILER】正在上映：" + str(now_playing_total))
        log.info("【HOT-TRAILER】检索即将上映电影...")
        page = 1
        upcoming = movie.upcoming(page)
        upcoming_total = 0
        while len(upcoming) > 0 and upcoming_total < hottrailer_total:
            upcoming_total = upcoming_total + len(upcoming)
            log.debug(">第 " + str(page) + " 页：" + str(upcoming_total))
            playing_list = playing_list + upcoming
            page = page + 1
            upcoming = movie.upcoming(page)
        log.info("【HOT-TRAILER】即将上映：" + str(upcoming_total))

        # 检索和下载预告片
        tmdb.language = 'en-US'
        total_count = 0
        fail_count = 0
        succ_count = 0
        notfound_count = 0
        for item in playing_list:
            total_count = total_count + 1
            try:
                movie_id = item.id
                movie_title = item.title
                log.info("【HOT-TRAILER】开始下载：" + movie_title + "...")
                if not is_chinese(movie_title):
                    log.info("【HOT-TRAILER】" + movie_title + " 没有中文看不懂，跳过...")
                    continue
                movie_year = item.release_date[0:4]
                log.info(str(total_count) + "、电影：" + str(movie_id) + " - " + movie_title)
                trailer_dir = hottrailer_path + "/" + movie_title + " (" + movie_year + ")"
                file_path = trailer_dir + "/" + movie_title + " (" + movie_year + ").%(ext)s"
                if os.path.exists(trailer_dir):
                    log.info("【HOT-TRAILER】" + movie_title + " 预告目录已存在，跳过...")
                    continue
                exists_flag = False
                for movie_type in movie_types:
                    movie_dir = os.path.join(movie_path, movie_type,  movie_title + " (" + movie_year + ")")
                    exists_trailers = get_dir_files_by_name(movie_dir, "-trailer.")
                    if len(exists_trailers) > 0:
                        log.info("【HOT-TRAILER】" + movie_title + " 电影目录已存在预告片，跳过...")
                        exists_flag = True
                        break
                if exists_flag:
                    continue
                # 开始下载
                try:
                    movie_videos = movie.videos(movie_id)
                except Exception as err:
                    log.error("【HOT-TRAILER】错误：" + str(err))
                    continue
                log.info("【HOT-TRAILER】" + movie_title + " 预告片总数：" + str(len(movie_videos)))
                if len(movie_videos) > 0:
                    succ_flag = False
                    for video in movie_videos:
                        trailer_key = video.key
                        log.debug(">下载：" + trailer_key)
                        exec_cmd = youtube_dl_cmd.replace("$PATH", file_path).replace("$KEY", trailer_key)
                        log.debug(">开始执行命令：" + exec_cmd)
                        # 获取命令结果
                        result_err, result_out = system_exec_command(exec_cmd, 600)
                        if result_err:
                            log.error("【HOT-TRAILER】" + movie_title + "-" + trailer_key + " 下载失败：" + result_err)
                        if result_out:
                            log.info("【HOT-TRAILER】" + movie_title + " 下载完成：" + result_out)
                        if result_err != "":
                            continue
                        else:
                            succ_flag = True
                            break
                    if succ_flag:
                        succ_count = succ_count + 1
                    else:
                        fail_count = fail_count + 1
                        shutil.rmtree(trailer_dir, ignore_errors=True)
                else:
                    notfound_count = notfound_count + 1
                    log.info("【HOT-TRAILER】" + movie_title + " 未检索到预告片")
            except Exception as err:
                log.error("【HOT-TRAILER】错误：" + str(err))
        # 发送消息
        end_time = datetime.now()
        sendmsg("【HotTrialer】电影预告更新完成", "耗时：" + str((end_time - start_time).seconds) + " 秒" +
                "\n\n总数：" + str(total_count) +
                "\n\n完成：" + str(succ_count) +
                "\n\n未找到：" + str(notfound_count) +
                "\n\n出错：" + str(fail_count))

    log.info("【HOT-TRAILER】开始转移存量预告片...")
    trailer_dir_list = os.listdir(hottrailer_path)
    for trailer_dir in trailer_dir_list:
        trailer_dir = os.path.join(hottrailer_path, trailer_dir)
        if os.path.isdir(trailer_dir):
            transfer_trailers(trailer_dir)
    log.info("【HOT-TRAILER】存量预告片转移完成！")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        flag = sys.argv[1] == "T" or False
    else:
        flag = False
    run_hottrailers(flag)
