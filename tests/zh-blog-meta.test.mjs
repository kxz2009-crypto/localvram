import test from 'node:test';
import assert from 'node:assert/strict';
import {resolveZhBlogTitle,extractFirstParagraph} from '../src/lib/zh-blog-meta.js';
test('section headings never replace distinct article titles',()=>{
 const body='## 快速结论\n\n文章正文。';
 assert.equal(resolveZhBlogTitle(body,'A model guide'),'A model guide');
 assert.notEqual(resolveZhBlogTitle(body,"Today's Local LLM Pick: qwen3:8b on RTX 3090 (2026)"),resolveZhBlogTitle(body,"Today's Local LLM Pick: ministral-3:14b on RTX 3090 (2026)"));
});
test('explicit article heading wins and translation comments do not leak into summaries',()=>{
 const body='<!--\nauto-translated\nstatus: translated\n-->\n# 具体文章标题\n\n## 快速结论\n\n这是文章的内容摘要。';
 assert.equal(resolveZhBlogTitle(body,'English title'),'具体文章标题');
 assert.equal(extractFirstParagraph(body),'这是文章的内容摘要。');
});
