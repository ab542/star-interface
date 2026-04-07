# OpenAPI 文件存放目录

## 说明
此目录用于存放 Star Digi+ 平台的 OpenAPI/Swagger 接口文档文件，用于自动生成接口测试用例 YAML 文件。

## 支持的文件格式
1. OpenAPI 3.0 / Swagger 2.0 格式
2. 文件扩展名支持：.json, .yaml, .yml

## 文件命名规范
- 使用模块命名，例如：login.json, workbench.yaml, monitor.json
- 全小写，使用下划线分隔单词，避免空格和特殊字符

## 文件内容要求
- 必须包含完整的 OpenAPI 规范结构
- paths 中必须定义所有接口路径、请求方法、参数、请求体、响应
- components/schemas 中定义数据模型

## 示例文件结构

### JSON 格式示例 (OpenAPI 3.0):
```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "Star Digi+ API",
    "version": "1.0.0"
  },
  "servers": [
    {
      "url": "https://star.digiplus-intl.com"
    }
  ],
  "paths": {
    "/api/media/advertiser/login": {
      "post": {
        "summary": "用户登录",
        "requestBody": {
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "email": {
                    "type": "string"
                  },
                  "password": {
                    "type": "string"
                  }
                },
                "required": ["email", "password"]
              }
            }
          }
        },
        "responses": {
          "200": {
            "description": "登录成功",
            "content": {
              "application/json": {
                "schema": {
                  "type": "object",
                  "properties": {
                    "code": {
                      "type": "integer"
                    },
                    "msg": {
                      "type": "string"
                    },
                    "data": {
                      "type": "object"
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### YAML 格式示例:
```yaml
openapi: 3.0.0
info:
  title: Star Digi+ API
  version: 1.0.0
servers:
  - url: https://star.digiplus-intl.com
paths:
  /api/media/advertiser/login:
    post:
      summary: 用户登录
      requestBody:
        content:
          application/json:
            schema:
              type: object
              properties:
                email:
                  type: string
                password:
                  type: string
              required:
                - email
                - password
      responses:
        '200':
          description: 登录成功
          content:
            application/json:
              schema:
                type: object
                properties:
                  code:
                    type: integer
                  msg:
                    type: string
                  data:
                    type: object
```

## 生成测试用例
将 OpenAPI 文件放入此目录后，即可基于该文件自动生成 `testdata/star_digi+/` 目录下对应的 YAML 测试用例文件。

## 注意事项
- 请确保 OpenAPI 文件完整，包含所有需要生成测试用例的接口
- 如果文件过大，可以按模块拆分多个文件
- 敏感信息（如认证token）不会保存在此文件中，测试用例会使用占位符或从配置读取
