# [Bangumi TV](https://bgm.tv/) MCP Service

这是一个MCP（机器通信协议）服务，提供对 BangumiTV API 的访问。它允许您与 BangumiTV 的数据进行交互，并检索有关动漫、漫画、音乐、游戏等的信息。

## 功能

共 **55 个工具**，完整覆盖 Bangumi API。

### 条目 (Subject)
- `get_daily_broadcast` - 每日放送
- `search_subjects` - 搜索条目
- `browse_subjects` - 浏览条目
- `get_subject_details` - 获取条目详情
- `get_subject_image` - 获取条目图片 URL
- `get_subject_persons` - 获取条目相关人员
- `get_subject_characters` - 获取条目相关角色
- `get_subject_relations` - 获取相关条目列表
- `get_episodes` - 获取章节列表
- `get_episode_details` - 获取章节详情

### 角色 (Character)
- `search_characters` - 搜索角色
- `get_character_details` - 获取角色详情
- `get_character_image` - 获取角色图片 URL
- `get_character_subjects` - 获取角色相关条目
- `get_character_persons` - 获取角色相关人员
- `collect_character` - 收藏角色（需认证）
- `uncollect_character` - 取消收藏角色（需认证）

### 人物 (Person)
- `search_persons` - 搜索人物
- `get_person_details` - 获取人物详情
- `get_person_image` - 获取人物图片 URL
- `get_person_subjects` - 获取人物相关条目
- `get_person_characters` - 获取人物相关角色
- `collect_person` - 收藏人物（需认证）
- `uncollect_person` - 取消收藏人物（需认证）

### 用户 (User)
- `get_user_info` - 获取用户信息
- `get_user_avatar` - 获取用户头像 URL
- `get_current_user` - 获取当前用户信息（需认证）

### 收藏 (Collection)
- `get_user_collections` - 获取用户收藏列表
- `get_user_subject_collection` - 获取用户条目收藏状态
- `update_subject_collection` - 更新条目收藏状态（需认证）
- `get_user_episode_collection` - 获取章节收藏列表（需认证）
- `update_episode_collection` - 批量更新章节收藏（需认证）
- `get_single_episode_collection` - 获取单章节收藏状态（需认证）
- `update_single_episode_collection` - 更新单章节收藏（需认证）
- `get_user_character_collections` - 获取用户角色收藏列表
- `get_user_character_collection` - 获取用户角色收藏状态
- `get_user_person_collections` - 获取用户人物收藏列表
- `get_user_person_collection` - 获取用户人物收藏状态

### 编辑历史 (Revision)
- `get_person_revisions` - 获取人物编辑历史
- `get_person_revision` - 获取人物单条编辑详情
- `get_character_revisions` - 获取角色编辑历史
- `get_character_revision` - 获取角色单条编辑详情
- `get_subject_revisions` - 获取条目编辑历史
- `get_subject_revision` - 获取条目单条编辑详情
- `get_episode_revisions` - 获取章节编辑历史
- `get_episode_revision` - 获取章节单条编辑详情

### 目录 (Index)
- `create_index` - 创建目录（需认证）
- `get_index` - 获取目录详情
- `update_index` - 更新目录信息（需认证）
- `get_index_subjects` - 获取目录内条目列表
- `add_subject_to_index` - 添加条目到目录（需认证）
- `update_index_subject` - 更新目录内条目信息（需认证）
- `remove_subject_from_index` - 从目录移除条目（需认证）
- `collect_index` - 收藏目录（需认证）
- `uncollect_index` - 取消收藏目录（需认证）

## 安装

```bash
# 克隆仓库
git clone https://github.com/Ukenn2112/BangumiMCP.git
cd BangumiMCP

# 创建并激活虚拟环境
uv venv
source .venv/bin/activate  # Linux/macOS
# 或在 Windows 上使用:
# .venv\Scripts\activate

# 安装依赖
uv add "mcp[cli]" requests httpx
```

## 使用（如Claude客户端）

URL: https://mcpcn.com/docs/quickstart/user/

claude_desktop_config.json
```json
{
    "mcpServers": {
        "bangumi-tv": {
            "command": "uv",
            "args": [
                "--directory",
                "/Users/Desktop/bangumi-tv", # 替换为你的目录
                "run",
                "main.py"
            ],
            "env": {
                "BANGUMI_TOKEN": "your_token_here" # 替换为你的 BangumiTV 令牌 （可选）如果你要查看或搜索R18内容
            }
        }
    }
}
```

## 环境变量

| 变量 | 必填 | 说明 |
|------|------|------|
| `BANGUMI_TOKEN` | 否 | Bangumi Access Token，用于需要认证的操作 |

## 致谢

此项目基于 Bangumi API 文档构建。
