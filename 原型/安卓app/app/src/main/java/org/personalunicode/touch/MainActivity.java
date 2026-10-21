package org.personalunicode.touch;

import android.app.Activity;
import android.os.Bundle;
import android.content.Intent;
import android.content.ClipData;
import android.content.ClipboardManager;
import android.graphics.Color;
import android.net.Uri;
import android.provider.DocumentsContract;
import android.database.Cursor;
import android.webkit.*;
import android.view.WindowInsets;
import android.widget.Toast;
import org.json.JSONObject;
import org.json.JSONArray;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.HashMap;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

public class MainActivity extends Activity {
    private static final String HOST="appassets.androidplatform.net";
    private WebView web;
    private String pendingExport;
    private String pendingTrime, pendingRelease;
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(244,244,239));
        getWindow().setNavigationBarColor(Color.rgb(244,244,239));
        web=new WebView(this);
        web.setBackgroundColor(Color.rgb(244,244,239));
        web.setOnApplyWindowInsetsListener((v,insets)->{
            if(android.os.Build.VERSION.SDK_INT>=30){android.graphics.Insets bars=insets.getInsets(WindowInsets.Type.systemBars()|WindowInsets.Type.displayCutout());v.setPadding(bars.left,bars.top,bars.right,bars.bottom);}
            return insets;
        });
        setContentView(web);
        web.getSettings().setJavaScriptEnabled(true);
        web.getSettings().setDomStorageEnabled(true);
        web.getSettings().setAllowFileAccess(false);
        web.getSettings().setAllowContentAccess(false);
        web.getSettings().setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setWebViewClient(new WebViewClient(){
            @Override public boolean shouldOverrideUrlLoading(WebView view,WebResourceRequest req){return true;}
            @Override public WebResourceResponse shouldInterceptRequest(WebView view,WebResourceRequest req){
                Uri url=req.getUrl();
                if(!"https".equals(url.getScheme())||!HOST.equals(url.getHost())||!"GET".equals(req.getMethod()))return errorResponse();
                String path=url.getPath();
                if(path==null||!path.startsWith("/assets/")||path.contains("..")||path.contains("\\"))return errorResponse();
                path=path.substring(8);
                String mime=path.endsWith(".js")?"application/javascript":path.endsWith(".css")?"text/css":path.endsWith(".json")?"application/json":path.endsWith(".woff2")?"font/woff2":path.endsWith(".html")?"text/html":"application/octet-stream";
                try{return new WebResourceResponse(mime,"UTF-8",getAssets().open(path));}catch(IOException e){return errorResponse();}
            }
        });
        web.addJavascriptInterface(new Files(),"AndroidFiles");
        web.loadUrl("https://"+HOST+"/assets/touch/index.html");
    }
    private WebResourceResponse errorResponse(){return new WebResourceResponse("text/plain","UTF-8",404,"Not Found",new HashMap<>(),new ByteArrayInputStream(new byte[0]));}
    private void message(String text){runOnUiThread(()->Toast.makeText(this,text,Toast.LENGTH_LONG).show());}
    public final class Files {
        @JavascriptInterface public void chooseTrimeDirectory(){runOnUiThread(()->{Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT_TREE);i.addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_PERSISTABLE_URI_PERMISSION);startActivityForResult(i,4);});}
        @JavascriptInterface public void writeTrimeDirectory(String raw,String id){
            if(raw.length()>4000000||!id.matches("unicode-[0-9]+-r[0-9]+")){message("草稿无效");return;}
            String saved=getPreferences(MODE_PRIVATE).getString("trimeTree",null);
            if(saved==null){message("先选择和同文相同的专用交接目录");releaseResult(id,false);return;}
            new Thread(()->{try{
                Uri tree=Uri.parse(saved),root=DocumentsContract.buildDocumentUriUsingTree(tree,DocumentsContract.getTreeDocumentId(tree));
                JSONObject manifest;try(InputStream in=getAssets().open("touch/trime-base/manifest.json")){manifest=new JSONObject(readText(in));}
                JSONArray list=manifest.getJSONArray("files");for(int j=0;j<list.length();j++){String name=list.getString(j);try(InputStream in=getAssets().open("touch/trime-base/"+name)){writeDocument(tree,root,name,in);}}
                JSONObject extra=new JSONObject(raw);java.util.Iterator<String> keys=extra.keys();boolean configPreserved=false;
                while(keys.hasNext()){String name=keys.next();if(!java.util.Arrays.asList("unicode_mobile.trime.yaml","default.custom.yaml","workspace-release.json","部署说明.txt","unicode-workspace-backup.json").contains(name))throw new IOException();String content=extra.getString(name);
                    if(name.equals("default.custom.yaml")){Uri existing=findDocument(tree,root,name);if(existing!=null){String previous;try(InputStream in=getContentResolver().openInputStream(existing)){previous=readText(in);}if(!previous.equals(content)){name="unicode_android.enable.yaml.example";configPreserved=true;}}}
                    try(InputStream in=new ByteArrayInputStream(content.getBytes(StandardCharsets.UTF_8))){writeDocument(tree,root,name,in);}
                }
                releaseResult(id,true);message(configPreserved?"部署文件已更新；原有 default.custom.yaml 已保留，请合并启用配置后同步部署":"部署文件已更新；请在同文同步、部署并测试");
            }catch(Exception e){message("目录更新未完成；检查目录授权后重试，不要部署不完整文件");releaseResult(id,false);}}).start();
        }
        @JavascriptInterface public void exportTrime(String files,String release){
            if(files.length()>4000000||!release.matches("unicode-[0-9]+-r[0-9]+")){message("部署草稿无效或过大");return;}
            runOnUiThread(()->{pendingTrime=files;pendingRelease=release;Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/zip");i.putExtra(Intent.EXTRA_TITLE,release+".zip");startActivityForResult(i,3);});
        }
        @JavascriptInterface public void exportLayout(String data){
            if(data.length()>8000000){message("布局过大，无法导出");return;}
            runOnUiThread(()->{pendingExport=data;Intent i=new Intent(Intent.ACTION_CREATE_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("application/json");i.putExtra(Intent.EXTRA_TITLE,"Unicode键位空间.json");startActivityForResult(i,1);});
        }
        @JavascriptInterface public void importLayout(){runOnUiThread(()->{Intent i=new Intent(Intent.ACTION_OPEN_DOCUMENT);i.addCategory(Intent.CATEGORY_OPENABLE);i.setType("*/*");startActivityForResult(i,2);});}
        @JavascriptInterface public void copyText(String text){runOnUiThread(()->((ClipboardManager)getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("Unicode",text)));}
    }
    @Override protected void onActivityResult(int request,int result,Intent data){
        super.onActivityResult(request,result,data);
        if(result!=RESULT_OK||data==null||data.getData()==null){if(request==1)pendingExport=null;if(request==3){releaseResult(pendingRelease,false);pendingTrime=null;pendingRelease=null;}return;}
        Uri uri=data.getData();
        if(request==4){try{getContentResolver().takePersistableUriPermission(uri,data.getFlags()&(Intent.FLAG_GRANT_READ_URI_PERMISSION|Intent.FLAG_GRANT_WRITE_URI_PERMISSION));getPreferences(MODE_PRIVATE).edit().putString("trimeTree",uri.toString()).apply();web.evaluateJavascript("window.trimeDirectorySelected()",null);}catch(Exception e){message("无法保存目录授权，请重新选择");}return;}
        if(request==3){final String raw=pendingTrime,id=pendingRelease;pendingTrime=null;pendingRelease=null;if(raw==null){message("部署草稿已失效，请重新生成");return;}new Thread(()->{
            try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")){if(out==null)throw new IOException();try(ZipOutputStream zip=new ZipOutputStream(out)){
                String manifest;try(InputStream in=getAssets().open("touch/trime-base/manifest.json");ByteArrayOutputStream bytes=new ByteArrayOutputStream()){byte[] b=new byte[4096];int n;while((n=in.read(b))!=-1)bytes.write(b,0,n);manifest=bytes.toString("UTF-8");}
                JSONArray names=new JSONObject(manifest).getJSONArray("files");byte[] buffer=new byte[16384];
                for(int j=0;j<names.length();j++){String name=names.getString(j);if(name.contains("..")||name.startsWith("/"))throw new IOException();zip.putNextEntry(new ZipEntry(name));try(InputStream in=getAssets().open("touch/trime-base/"+name)){int n;while((n=in.read(buffer))!=-1)zip.write(buffer,0,n);}zip.closeEntry();}
                JSONObject extra=new JSONObject(raw);java.util.Iterator<String> keys=extra.keys();while(keys.hasNext()){String name=keys.next();if(!java.util.Arrays.asList("unicode_mobile.trime.yaml","default.custom.yaml","workspace-release.json","部署说明.txt","unicode-workspace-backup.json").contains(name))throw new IOException();zip.putNextEntry(new ZipEntry(name));zip.write(extra.getString(name).getBytes(StandardCharsets.UTF_8));zip.closeEntry();}
            }releaseResult(id,true);}catch(Exception e){message("部署包导出失败，草稿保留");releaseResult(id,false);}
        }).start();}
        if(request==1){final String value=pendingExport;pendingExport=null;if(value==null){message("导出内容已失效，请重新导出");return;}new Thread(()->{try(OutputStream out=getContentResolver().openOutputStream(uri,"wt")){if(out==null)throw new IOException();out.write(value.getBytes(StandardCharsets.UTF_8));message("布局已导出");}catch(Exception e){message("导出失败，请重新选择文件位置");}}).start();}
        if(request==2)new Thread(()->{try(InputStream in=getContentResolver().openInputStream(uri);ByteArrayOutputStream bytes=new ByteArrayOutputStream()){
            if(in==null)throw new IOException();byte[] buffer=new byte[8192];int n;while((n=in.read(buffer))!=-1){bytes.write(buffer,0,n);if(bytes.size()>8000000)throw new IOException("文件超过 8 MB");}
            String text=bytes.toString("UTF-8");runOnUiThread(()->web.evaluateJavascript("window.receiveLayout("+JSONObject.quote(text)+")",null));
        }catch(Exception e){message("读取布局失败或文件超过 8 MB");}}).start();
    }
    private void releaseResult(String id,boolean success){if(id!=null)runOnUiThread(()->web.evaluateJavascript("window.trimeExportFinished("+JSONObject.quote(id)+","+success+")",null));}
    private String readText(InputStream in)throws IOException{if(in==null)throw new IOException();ByteArrayOutputStream b=new ByteArrayOutputStream();byte[] a=new byte[4096];int n;while((n=in.read(a))!=-1)b.write(a,0,n);return b.toString("UTF-8");}
    private Uri findDocument(Uri tree,Uri parent,String name)throws IOException{
        Uri children=DocumentsContract.buildChildDocumentsUriUsingTree(tree,DocumentsContract.getDocumentId(parent));
        try(Cursor c=getContentResolver().query(children,new String[]{DocumentsContract.Document.COLUMN_DOCUMENT_ID,DocumentsContract.Document.COLUMN_DISPLAY_NAME},null,null,null)){if(c==null)throw new IOException();while(c.moveToNext())if(name.equals(c.getString(1)))return DocumentsContract.buildDocumentUriUsingTree(tree,c.getString(0));}return null;
    }
    private void writeDocument(Uri tree,Uri root,String path,InputStream in)throws IOException{
        if(path.startsWith("/")||path.contains("..")||path.contains("\\"))throw new IOException();String[] names=path.split("/");Uri parent=root;
        for(int j=0;j<names.length-1;j++){Uri found=findDocument(tree,parent,names[j]);parent=found!=null?found:DocumentsContract.createDocument(getContentResolver(),parent,DocumentsContract.Document.MIME_TYPE_DIR,names[j]);if(parent==null)throw new IOException();}
        String name=names[names.length-1];Uri file=findDocument(tree,parent,name);if(file==null)file=DocumentsContract.createDocument(getContentResolver(),parent,"application/octet-stream",name);if(file==null)throw new IOException();
        try(OutputStream out=getContentResolver().openOutputStream(file,"wt")){if(out==null)throw new IOException();byte[] b=new byte[16384];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}
    }
    @Override public void onBackPressed(){web.evaluateJavascript("(()=>{const d=document.querySelector('dialog[open]');if(d){d.close();return true;}return false;})()",value->{if(!"true".equals(value))super.onBackPressed();});}
    @Override protected void onDestroy(){web.removeJavascriptInterface("AndroidFiles");web.destroy();super.onDestroy();}
}
