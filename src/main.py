
import sys
import time
import json
import threading
import traceback
import requests
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import Pool
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import QUrl, QThread, pyqtSignal
from ui.ui import Ui_MainWindow
from time import sleep


class LolQueryMain(QMainWindow, Ui_MainWindow):

    def __init__(self, parent=None):
        super(LolQueryMain, self).__init__(parent)
        self.setupUi(self)
        # self.connectSlots()
        self.account_ls = []

    def connectSlots(self):
        # 设置信号
        self.toolButton_2.clicked.connect(self.slot_btn_chooseDir)
        # 开始
        self.toolButton.clicked.connect(self.start_crawler)

        # 结束任务
        self.toolButton_3.clicked.connect(self.stop_crawler)

        # 打开文件位置
        self.toolButton_4.clicked.connect(lambda: QDesktopServices.openUrl(QUrl('./tmp')))

    def stop_crawler(self):
        self.statusBar().showMessage('全部暂停')
        self.updateItem("全部停止抓取")
        self.job.stop()

    def start_crawler(self):
        self.statusBar().showMessage('全部开始')
        print("开始抓取\n")
        # 创建线程
        self.updateItem("开始抓取")
        proxy_text = self.lineEdit.text()
        # print(proxy_text)
        # proxy_text = None
        # if proxy_text:
        #     proxy_text
        self.job = Job(self.account_ls, proxy_text=proxy_text)
        self.job.signal2.connect(self.updateItem)
        self.job.start()
        self.job.exec()

    def updateItem(self, data):
        cursor = self.textBrowser.textCursor()
        cursor.movePosition(QTextCursor.End)
        show_time = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        str = "[" + show_time + "]" + "   " + data + "\n"
        cursor.insertText(str)
        self.textBrowser.setTextCursor(cursor)
        self.textBrowser.ensureCursorVisible()


        # 更新table
        # header = ['账号', '游戏区', '昵称', '等级', '精粹', '英雄数', '皮肤数', '单/双排位赛', '灵活组排5v5', '灵活组排3v3']
        # row = self.tableWidget.rowCount()
        # print(row)
        # self.tableWidget.insertRow(row)
        # for i, x in enumerate(header):
        #     try:
        #         self.tableWidget.setItem(row, i, QTableWidgetItem(data[i]))
        #     except Exception as e:
        #         pass

    def slot_btn_chooseDir(self):
        fileName_choose, filetype = QFileDialog.getOpenFileName(self,
                                                                "选取文件",
                                                                "All Files (*);;Text Files (*.txt)")  # 设置文件扩展名过滤,用双分号间隔

        if fileName_choose == "":
            print("\n取消选择")
            return

        print("\n你选择的文件为:")
        print(fileName_choose)
        print("文件筛选器类型: ", filetype)
        # 解析账号文件

        with open(fileName_choose, "r") as f:
            account_info = f.readlines()
            for x in account_info:
                x = x.strip()
                if x:
                    dic = {}
                    print(x)
                    ls = x.split("----")
                    dic["account_name"] = ls[0]
                    dic["password"] = ls[1]
                    self.account_ls.append(dic)
        print(self.account_ls)
        self.statusbar.showMessage("上传账号位置及名称:" + fileName_choose)


# 注意这里使用的是qt自己本身的线程，而不能用python自己的线程
class Job(QThread):
    signal2 = pyqtSignal(str)

    def signal2emit(self, data):
        print(data)
        self.signal2.emit(data)  # 朝connect的函数发射一个tuple

    def __init__(self, account_ls, proxy_text=None, *args, **kwargs):
        self.__flag = threading.Event()  # 用于暂停线程的标识
        super(Job, self).__init__(*args, **kwargs)
        self.account_ls = account_ls
        self.proxy_text = proxy_text
        self.__flag.set()    # 设置为True
        self.__running = threading.Event()   # 用于停止线程的标识
        self.__running.set()   # 将running设置为True

        self.play_info = "https://lol.ams.game.qq.com/lol/autocms/v1/transit/LOL/LOLWeb/Official/PlayerInfo"
        self.play_honor = "https://lol.ams.game.qq.com/lol/autocms/v1/transit/LOL/LOLWeb/Official/PlayerChampSkin,PlayerHonor,PlayerBattleSummary"
        self.play_property = "https://lol.ams.game.qq.com/lol/autocms/v1/transit/LOL/LOLWeb/Official/PlayerProperty,PlayerRankInfo,PlayerFavChamps"

        # self.signal2.connect(setItem)#连接发射函数

    def spider(self, account):
        if self.__running.isSet():
            self.__flag.wait()
            account_name = account["account_name"]
            password = account["password"]
            account_str = account_name + "----" + password
            init_driver = DriverSrivice(is_proxy=self.proxy_text)
            driver = init_driver.driver
            self.proxy_ip = init_driver.proxy_ip
            self.proxy_port = init_driver.proxy_port
            try:
                if init_driver.request_times <= 2:
                    init_driver.start_spider()
                    try:
                        driver.switch_to_frame(driver.find_element_by_id("loginIframe"))
                    except NoSuchElementException as e:
                        print("重新请求1")
                        update_str = account_str + "=>" + "重新请求"
                        self.signal2.emit(update_str)
                        init_driver.request_times = init_driver.request_times + 1
                        init_driver.start_spider()

                    try:
                        element = WebDriverWait(driver, 5, 0.5).until(
                            EC.presence_of_element_located((By.ID, "switcher_plogin")))
                        # element = driver.find_element_by_id("switcher_plogin")
                        element.click()
                    except ElementNotInteractableException as e:
                        init_driver.request_times = init_driver.request_times + 1
                        update_str = account_str + "=>" + "重新请求"
                        self.signal2.emit(update_str)
                        init_driver.start_spider()

                    sleep(1)
                    driver.find_element_by_id('u').clear()
                    driver.find_element_by_id('u').send_keys(account_name)
                    driver.find_element_by_id('p').clear()
                    driver.find_element_by_id('p').send_keys(password)
                    sleep(1)
                    driver.find_element_by_id('login_button').click()
                    sleep(5)
                    try:
                        iframe = driver.find_element_by_id('tcaptcha_iframe')
                    except Exception as e:
                        print('get iframe failed: ', e)
                    else:
                        sleep(2)  # 等待资源加载
                        driver.switch_to.frame(iframe)

                    try:
                        # 等待图片加载出来
                        button = WebDriverWait(driver, 5, 0.5).until(EC.presence_of_element_located((By.ID,
                                                                                                     "tcaptcha_drag_button")))
                        # button = driver.find_element_by_id('tcaptcha_drag_button')
                    except Exception as e:
                        print('get button failed: ', e)
                    sleep(1)
                    # 开始拖动 perform()用来执行ActionChains中存储的行为
                    flag = 0
                    distance = 195
                    offset = 5
                    times = 0
                    cookies = {}
                    while 1:
                        if times >= 7:
                            is_continue = False
                            print("超过滑块验证测试")
                            update_str = account_str + "=>" + "超过滑块验证测试"
                            self.signal2.emit(update_str)
                            break
                        action = ActionChains(driver)
                        action.reset_actions()  # 清除之前的action
                        action.click_and_hold(button).perform()
                        # action.reset_actions()  # 清除之前的action
                        print(distance)
                        # track = get_track(distance)
                        # for i in track:
                        # action.move_by_offset(xoffset=distance, yoffset=0).perform()
                        # action.reset_actions()
                        sleep(0.5)
                        try:
                            action.move_by_offset(xoffset=distance, yoffset=0).perform()
                            action.release().perform()
                            sleep(5)
                        except Exception as e:
                            print("出现异常", e)

                        # 判断某元素是否被加载到DOM树里，并不代表该元素一定可见
                        try:
                            alert = driver.find_element_by_id('guideText').text
                            print(alert)
                        except Exception as e:
                            print('get alert error: %s' % e)
                            alert = ''
                        if alert:
                            print(u'滑块位移需要调整: %s' % alert)

                            update_str = account_str + "=>" + u'滑块位移需要调整: %s' % alert
                            self.signal2.emit(update_str)
                            distance -= offset
                            times += 1
                            print("滑块验证次数" + str(times))
                            desc = "滑块验证次数" + str(times)

                            update_str = account_str + "=>" + desc
                            self.signal2.emit(update_str)
                            sleep(4)

                        else:
                            desc = "滑块验证通过"
                            print('滑块验证通过')
                            update_str = account_str + "=>" + '滑块验证通过'
                            self.signal2.emit(update_str)
                            try:
                                driver.switch_to.default_content()
                                sleep(2)
                                opt = WebDriverWait(driver, 5, 0.5).until(EC.presence_of_element_located((By.ID,
                                                                                                          "areaContentId_lol")))
                                # opt = driver.find_element_by_id('areaContentId_lol')
                                sleep(2)
                                Select(opt).select_by_index(1)
                                WebDriverWait(driver, 5, 0.5).until(
                                    EC.presence_of_element_located((By.ID, "confirmButtonId_lol")))

                                driver.find_element_by_id("confirmButtonId_lol").click()
                                # sleep(2)
                                cookies = driver.get_cookies()
                                is_continue = True
                                break
                            except Exception as e:
                                traceback.print_exc()
                                driver.close()
                                print(e)
                                is_continue = False
                                desc = "登录失败,请检查登录密码或者网络环境"
                                print("登录失败,请检查登录密码或者网络环境")
                                update_str = account_str + "=>" + desc
                                self.signal2.emit(update_str)
                                break
                    #
                    # cookies = self.driver.get_cookies()
                    # self.driver.close()
                    # is_continue = True
                    if is_continue:
                        area_ls = [{"t": "艾欧尼亚  电信", "v": "1", "status": "1"},
                                   {"t": "比尔吉沃特  网通", "v": "2", "status": "1"},
                                   {"t": "祖安 电信", "v": "3", "status": "1"},
                                   {"t": "诺克萨斯电信", "v": "4", "status": "1"},
                                   {"t": "德玛西亚 网通", "v": "6", "status": "1"},
                                   {"t": "班德尔城 电信", "v": "5", "status": "1"},
                                   {"t": "皮尔特沃夫 电信", "v": "7", "status": "1"},
                                   {"t": "战争学院 电信", "v": "8", "status": "1"},
                                   {"t": "弗雷尔卓德 网通", "v": "9", "status": "1"},
                                   {"t": "巨神峰 电信", "v": "10", "status": "1"},
                                   {"t": "雷瑟守备 电信", "v": "11", "status": "1"},
                                   {"t": "无畏先锋 网通", "v": "12", "status": "1"},
                                   {"t": "裁决之地 电信", "v": "13", "status": "1"},
                                   {"t": "黑色玫瑰 电信", "v": "14", "status": "1"},
                                   {"t": "暗影岛 电信", "v": "15", "status": "1"},
                                   {"t": "钢铁烈阳 电信", "v": "17", "status": "1"},
                                   {"t": "恕瑞玛 网通", "v": "16", "status": "1"},
                                   {"t": "水晶之痕 电信", "v": "18", "status": "1"},
                                   {"t": "教育网专区", "v": "21", "status": "1"},
                                   {"t": "影流 电信", "v": "22", "status": "1"},
                                   {"t": "守望之海 电信", "v": "23", "status": "1"},
                                   {"t": "扭曲丛林 网通", "v": "20", "status": "1"},
                                   {"t": "征服之海 电信", "v": "24", "status": "1"},
                                   {"t": "卡拉曼达 电信", "v": "25", "status": "1"},
                                   {"t": "皮城警备 电信", "v": "27", "status": "1"},
                                   {"t": "巨龙之巢 网通", "v": "26", "status": "1"},
                                   {"t": "男爵领域 全网络", "v": "30", "status": "1"},
                                   {"t": "均衡教派", "v": "19", "status": "1"}]

                        file = open('./tmp/hero_info.txt', 'a+')
                        for area_info in area_ls:
                            dic = {}
                            area_no = area_info["v"]
                            dic["area_name"] = area_info["t"]
                            # 等级及昵称
                            player_info = self.get_player_info(cookies, area_no)
                            if "code" in player_info.keys():
                                if player_info["code"] == -601:
                                    dic["role_ixexit"] = 0
                                    update_str = account_str + "=>" + dic["area_name"] + "----不存在角色"
                                    self.signal2.emit(update_str)
                                    print("不存在角色")

                                    continue
                            if player_info["retCode"] == 0:
                                dic["role_ixexit"] = 1
                                dic["player_name"] = player_info["name"]
                                dic["player_level"] = player_info["level"]

                            # 英雄数据量及皮肤数量
                            player_honor = self.get_player_honor(cookies, area_no)
                            if "PlayerChampSkin" in player_honor.keys():
                                dic["player_champion_num"] = player_honor["PlayerChampSkin"]["msg"]["data"][
                                    "champion_num"]
                                dic["player_skin_num"] = player_honor["PlayerChampSkin"]["msg"]["data"]["skin_num"]

                            # 获取精粹和段位
                            player_property = self.get_player_property(cookies, area_no)
                            if "PlayerProperty" in player_property.keys():
                                dic["player_ip_amount"] = player_property["PlayerProperty"]["msg"]["ip_amount"]

                            # hero_data = selenium.get_hero_data(area_info, cookies)
                            # print(hero_data)
                            # self.signal2emit(hero_data)
                            # time.sleep(2)

                            update_str = account_str + "=>" + dic["area_name"] + "----昵称:" + \
                                         dic["player_name"] + "----等级:" + str(dic["player_level"]) + "----皮肤数量:" + \
                                         str(dic["player_skin_num"]) + "----英雄数量:" + str(dic["player_champion_num"]) + \
                                         "----精粹数量:" + str(dic["player_ip_amount"]) + "----精粹数量:" + "暂无段位"

                            file.write(update_str + "\n")
                            self.signal2.emit(update_str)
                        file.close()

                else:
                    driver.close()
                    update_str = account_str + "=>" + "超过重新请求次数"
                    self.signal2.emit(update_str)
                    print("超过重新请求次数")
            except Exception as e:
                print(e)
                driver.close()
                update_str = account_str + "=>" + "获取账号信息失败"
                self.signal2.emit(update_str)

    def run(self):
        # global SystemTime,TimePice#声明要用的全局变量
        # self.__flag.wait()   # 为True时立即返回, 为False时阻塞直到内部的标识位为True后返回
        ###################
        #这里写线程要干的事情#
        ###################

        pool = ThreadPoolExecutor(5)
        for account in self.account_ls:
            pool.submit(self.spider, account)

        # p = Pool(5)
        # p.map(self.spider, self.account_ls)
        # p.close()
        # p.join()

    def pause(self):
        self.__flag.clear()   # 设置为False, 让线程阻塞

    def resume(self):
        self.__flag.set()  # 设置为True, 让线程停止阻塞

    def stop(self):
        self.__flag.set()    # 将线程从暂停状态恢复, 如何已经暂停的话
        self.__running.clear()    # 设置为False

    def get_hero_data(self, area_info, cookies):
        dic = {}
        area_no = area_info["v"]
        dic["area_name"] = area_info["t"]
        # 等级及昵称
        player_info = self.get_player_info(cookies, area_no)
        if "code" in player_info.keys():
            if player_info["code"] == -601:
                dic["role_ixexit"] = 0
                print("不存在角色")
                return
        if player_info["retCode"] == 0:
            dic["role_ixexit"] = 1
            dic["player_name"] = player_info["name"]
            dic["player_level"] = player_info["level"]

        # 英雄数据量及皮肤数量
        player_honor = self.get_player_honor(cookies, area_no)
        if "PlayerChampSkin" in player_honor.keys():
            dic["player_champion_num"] = player_honor["PlayerChampSkin"]["msg"]["data"]["champion_num"]
            dic["player_skin_num"] = player_honor["PlayerChampSkin"]["msg"]["data"]["skin_num"]

        # 获取精粹和段位
        player_property = self.get_player_property(cookies, area_no)
        if "PlayerProperty" in player_property.keys():
            dic["player_ip_amount"] = player_property["PlayerProperty"]["msg"]["ip_amount"]

        # if "PlayerProperty" in player_property.keys():
        #     dic["player_ip_amount"] = player_honor["PlayerProperty"]["msg"]["ip_amount"]
        return dic

    def get_player_property(self, cookies, area_no):
        s = requests.session()
        s.verify = False
        s.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
        }
        # 这里我们使用cookie对象进行处理
        jar = RequestsCookieJar()
        for cookie in cookies:
            jar.set(cookie['name'], cookie['value'])
        payload = ""

        querystring = {"use": "acc", "area": area_no}
        if self.proxy_text:
            proxies = {'http': 'http://' + self.proxy_ip + ':' + str(self.proxy_port)}
        else:
            proxies = None
        resp = s.get(self.play_property, cookies=jar, data=payload, params=querystring, proxies=proxies)
        print(json.loads(str(resp.content, encoding="utf-8")))
        play_property = json.loads(str(resp.content, encoding="utf-8"))
        return play_property

    # 获取所有大区的用户信息
    def get_player_honor(self, cookies, area_no):
        s = requests.session()
        s.verify = False
        s.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
        }
        # 这里我们使用cookie对象进行处理
        jar = RequestsCookieJar()
        for cookie in cookies:
            jar.set(cookie['name'], cookie['value'])
        payload = ""

        querystring = {"use": "acc", "area": area_no}
        if self.proxy_text:
            proxies = {'http': 'http://' + self.proxy_ip + ':' + str(self.proxy_port)}
        else:
            proxies = None
        resp = s.get(self.play_honor, cookies=jar, data=payload, params=querystring, proxies=proxies)
        print(json.loads(str(resp.content, encoding="utf-8")))
        play_honor = json.loads(str(resp.content, encoding="utf-8"))
        return play_honor

    def get_player_info(self, cookies, area_no):
        s = requests.session()
        s.verify = False
        s.headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/73.0.3683.103 Safari/537.36"
        }
        # 这里我们使用cookie对象进行处理
        jar = RequestsCookieJar()
        for cookie in cookies:
            jar.set(cookie['name'], cookie['value'])
        payload = ""

        querystring = {"use": "acc", "area": area_no}
        if self.proxy_text:
            proxies = {'http': 'http://' + self.proxy_ip + ':' + str(self.proxy_port)}
        else:
            proxies = None
        resp = s.get(self.play_info, cookies=jar, data=payload, params=querystring, proxies=proxies)
        print(json.loads(str(resp.content, encoding="utf-8")))
        player_info = json.loads(str(resp.content, encoding="utf-8"))
        return player_info


def main():
    app = QApplication(sys.argv)
    w = LolQueryMain()
    w.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()