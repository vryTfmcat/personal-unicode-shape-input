package org.personalunicode.touch;

import android.app.Instrumentation;
import android.app.Activity;
import android.os.Bundle;
import android.graphics.Typeface;
import android.graphics.Paint;
import android.graphics.Bitmap;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.fonts.Font;
import android.graphics.fonts.FontFamily;
import org.json.JSONObject;
import org.json.JSONArray;
import java.io.*;
import java.util.ArrayList;

/** Device-side font loading and shaping probe. No interaction with user input or other apps. */
public class FontProbe extends Instrumentation {
 @Override public void onCreate(Bundle b){super.onCreate(b);start();}
 private String read(InputStream in)throws Exception{try(InputStream source=in;ByteArrayOutputStream out=new ByteArrayOutputStream()){byte[] b=new byte[8192];int n;while((n=source.read(b))!=-1)out.write(b,0,n);return out.toString("UTF-8");}}
 @Override public void onStart(){new Thread(()->{
  Bundle result=new Bundle();
  try{
   JSONObject manifest=new JSONObject(read(getTargetContext().getAssets().open("touch/trime-base/manifest.json")));
   JSONArray names=manifest.getJSONArray("fonts");ArrayList<FontFamily> families=new ArrayList<>();
   for(int i=0;i<names.length();i++){
    String name=names.getString(i);File dir=new File(getTargetContext().getCacheDir(),"font-probe");if(!dir.isDirectory()&&!dir.mkdirs())throw new IOException("Cannot create probe directory");File file=new File(dir,name);
    try(InputStream in=getTargetContext().getAssets().open("touch/trime-base/fonts/"+name);OutputStream out=new FileOutputStream(file)){byte[] b=new byte[16384];int n;while((n=in.read(b))!=-1)out.write(b,0,n);}
    families.add(new FontFamily.Builder(new Font.Builder(file).build()).build());
   }
   Typeface.CustomFallbackBuilder builder=new Typeface.CustomFallbackBuilder(families.get(0));for(int i=1;i<families.size();i++)builder.addCustomFallback(families.get(i));
   Paint paint=new Paint();paint.setTypeface(builder.setSystemFallback("sans-serif").build());paint.setTextSize(48);
   Bitmap bitmap=Bitmap.createBitmap(1200,1100,Bitmap.Config.ARGB_8888);Canvas canvas=new Canvas(bitmap);canvas.drawColor(Color.WHITE);paint.setColor(Color.BLACK);
   String sample="中区块全形收藏混合模式符号空格 ABC Ⱝ 𓆟 𒁔 𝄞";
   Typeface[] faces={paint.getTypeface(),Typeface.DEFAULT,new Typeface.CustomFallbackBuilder(families.get(34)).setSystemFallback("sans-serif").build()};
   for(int j=0;j<faces.length;j++){paint.setTypeface(faces[j]);canvas.drawText(sample,20,100+j*150,paint);canvas.drawText("row "+j+" metrics "+paint.getFontMetrics().ascent+" / "+paint.getFontMetrics().descent,20,160+j*150,paint);}
   try(OutputStream out=new FileOutputStream(new File(getTargetContext().getCacheDir(),"font-probe.png"))){bitmap.compress(Bitmap.CompressFormat.PNG,100,out);}
   paint.setTypeface(faces[0]);
   int[] samples={0x4e2d,0x533a,0x7a7a,0xfe5d,0x107a8,0x3010,0xff62,0xa784,0x2c2d,0x1319f,0x12054,0x25cb,0x1d11e,0x20000,0x30000,0x31350,0x323b0};
   StringBuilder details=new StringBuilder();for(int cp:samples){String s=new String(Character.toChars(cp));boolean ok=paint.hasGlyph(s);Bitmap cell=Bitmap.createBitmap(256,256,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(cell);c.drawColor(Color.WHITE);c.drawText(s,64,128,paint);int ink=0;for(int y=0;y<256;y++)for(int x=0;x<256;x++)if(cell.getPixel(x,y)!=Color.WHITE)ink++;cell.recycle();details.append(Integer.toHexString(cp)).append('=').append(ok).append('/').append(ink).append(';');if(!ok||ink<3)throw new Exception("Missing or blank device glyph U+"+Integer.toHexString(cp)+" pixels="+ink);}
   result.putString("stream","PASS: "+families.size()+" native families loaded; "+details);finish(Activity.RESULT_OK,result);
  }catch(Throwable e){result.putString("stream","FAIL: "+e);finish(Activity.RESULT_CANCELED,result);}
 }).start();}
}
