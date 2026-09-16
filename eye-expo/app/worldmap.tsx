
import React,{useEffect,useState} from 'react'
import {View,Text,FlatList,StyleSheet} from 'react-native'
type WorldObject = { id: string; title: string }
export default function WorldMap(){
 const [data,setData]=useState<WorldObject[]>([])
 useEffect(()=>{
  fetch('/v1/world/objects').then(r=>r.json()).then(d=>setData(d.objects||[]))
 },[])
 return(
  <View style={s.c}>
   <Text style={s.t}>Object World Map</Text>
   <FlatList data={data} keyExtractor={i=>i.id} renderItem={({item})=>(<Text style={s.r}>{item.title}</Text>)}/>
  </View>
 )
}
const s=StyleSheet.create({c:{flex:1,backgroundColor:"#000",padding:20},t:{color:"#fff",fontSize:22},r:{color:"#ccc"}})
