# Android 初步版本 0.2.4

本版本将触屏 Unicode 编辑器与同文 Trime 配合使用，实际手机已确认候选输入、固定目录发布、按钮配色与补缺字体恢复正常。完整功能、限制及验收记录见 [README](README.md)。

## 下载和安装

GitHub Release 标签为 `android-v0.2.4`，提供以下文件及 SHA256：

- `Unicode符号拼排-0.2.4-debug.apk`：编辑器，Android 8 以上；完整同文字体回退需要 Android 10 以上。属于开发签名的初步版本。
- `Unicode-Trime-0.2.4.zip`：独立安卓 Rime 方案、手机键盘主题、词典和字体。需另行安装官方同文 Trime。
- `Unicode-Android-BuildInputs-0.2.4.zip`：重建输入快照，包括生成字符表、阶段数据、全形核对索引及已验证的原生字体缓存。不是用户手机草稿备份。

将部署 ZIP 解压到同文授权的外部目录，执行同步和部署，选择“Unicode 安卓三模式”及“Unicode 手机三模式”。后续编辑器可授权同一目录并更新文件，再由同文同步部署。不要在文件更新过程中同步。

## 从源码重建

1. 检出 `android-v0.2.4`。将 BuildInputs ZIP 解压到工程根目录，保留内部相对路径；只在该版本的干净检出中使用，避免覆盖后续自己的阶段数据。
2. Python 3 安装 `fonttools[woff]`、`Brotli`、`Pillow`、`numpy`、`PyYAML`。原生字体缓存可直接复用，无需本机原字体目录；从头重新生成字体的来源要求见 [字体说明](../键位编辑器/fonts/README.md)。
3. 准备 JDK 17、Android SDK 35，在本目录 `local.properties` 设置 `sdk.dir`，配置 `JAVA_HOME`。
4. 在本目录运行 `gradlew.bat assembleDebug`，或在其他平台运行 `sh ./gradlew assembleDebug`。首次构建需下载 Gradle 与 Android 构建依赖。
5. APK 位于 `app/build/outputs/apk/debug/app-debug.apk`。在工程根目录运行 `node 工具/package_trime.cjs` 可生成基线部署文件。

源码保存触屏界面、Android 工程、构建工具及字库依赖；大体积可再生成输入放在 Release。机器路径、SDK、构建输出、调试截图和旧版本安装包不进入本次源码提交。

## 版本范围

保留区块、全形、收藏，支持个人中文名称、标签、反查、最近使用、自由拼排、手机键位配置、草稿快照及部署包。完整改码、编码格位、画布分组分页仍待后续开发。全形分类及键义仍属待核对方案，不能视为已全部人工确认。

字体映射覆盖当前 159,345 个字符；17 个真机样本检查了实际绘制像素，不代表所有字符组合均已验收。补缺只作用于同文；接收应用及对方设备仍使用各自字体。0.2.3 的空白字形回归已修复，不应回退使用。
