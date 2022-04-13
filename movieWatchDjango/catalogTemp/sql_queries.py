listUserGroups = "select * from catalogTemp_usergroup where groupID in (select groupID_id from " \
                 "catalogTemp_groupmembers where userID_id = {0})"
list_user_group_query = "select * from catalogTemp_usergroup where groupID in (select groupID_id from " \
                 "catalogTemp_groupmembers where userID_id = {0})"
listGroupMembers = "select * from auth_user where id in (select userID_id from catalogTemp_groupmembers where groupID_id = {0})"
list_group_members_query = "select first_name, last_name, username, id from auth_user where id in (select userID_id from catalogTemp_groupmembers where groupID_id = {0})"
listMovieRecsByGroups="select movieRecID, movieID_id, recommenderUserID_id, recommendationDesc, reccomenderRating," \
                      " createdAt, updatedAt from catalogTemp_movierecommendation where movieRecID in" \
                      " (select recID_id from catalogTemp_movierecommendationwithingroup where groupID_id = {0})"
selectMovieRecAndMovie = "select movieRecID, recommendationDesc, reccomenderRating, createdAt," \
                         " updatedAt, recommenderUserID_id, movieID, movieTitle, " \
                         "director, description, runtime, genre, notableCast, yearReleased" \
                         " from catalogTemp_movierecommendation as f" \
                         " join catalogTemp_movie t on f.movieID_id = t.movieID where movieRecID = {0}"
movieRecAndMovieQueryset = "select movieRecID, recommendationDesc, reccomenderRating, createdAt, " \
                           "updatedAt, recommenderUserID_id, movieID, movieTitle, director, description, runtime," \
                           " genre, notableCast, yearReleased from catalogTemp_movierecommendation" \
                           " as f join catalogTemp_movie t on f.movieID_id = t.movieID where movieRecID = {0}"
commentsByPost = "select * from catalogTemp_commentonmovierecommendation where postID_id = {0}"
getUsersWhoEndorsePosts = "select * from auth_user where id in (select endorserUserID_id " \
                          "from catalogTemp_endorsementsonmovierecsingroups where postID_id = {0})"
getUsersWhoLikeAComment = "select * from auth_user where id in (select userID_id from catalogTemp_likesoncommentsonposts where commentID_id = {0})"
listMovieRecsByGroupsUserIn = "select movieRecID, movieID_id, recommenderUserID_id, recommendationDesc, reccomenderRating, createdAt, updatedAt " \
                              "from catalogTemp_movierecommendation where movieRecID in (select recID_id from catalogTemp_movierecommendationwithingroup where groupID_id in (select groupID_id from catalogTemp_groupmembers where userID_id = {0}))"

getCommonGroups = "select * from catalogTemp_usergroup where groupID in (select groupID_id from catalogTemp_groupmembers where userID_id = {0}) and groupID " \
                  "in (select groupID from catalogTemp_usergroup where groupID in" \
                  " (select groupID_id from catalogTemp_groupmembers where userID_id = {1}));"

getCommonGroupsOnPost = "select groupID, groupName, groupDesc, createdAt, updatedAt, createrUserID_id, groupJoinCode from catalogTemp_usergroup where groupID in " \
                  "(select groupID_id from catalogTemp_groupmembers where userID_id = {0}) and groupID in (select groupID from catalogTemp_usergroup where groupID in (select groupID_id from catalogTemp_groupmembers where userID_id = {1})) and groupID in (select groupID_id from catalogTemp_movierecommendationwithingroup where recID_id = {2});"
getCommonFeed = "select * from catalogTemp_movierecommendation where movieRecID in (select recID_id from catalogTemp_movierecommendationwithingroup where " \
                "groupID_id in (select groupID from catalogTemp_usergroup where groupID in (select groupID_id from" \
                " catalogTemp_groupmembers where userID_id = {0}))) and movieRecID in" \
                " (select recID_id from catalogTemp_movierecommendationwithingroup where" \
                " groupID_id in (select groupID from catalogTemp_usergroup where groupID in (select groupID_id from" \
                " catalogTemp_groupmembers where userID_id = {1})));"
listGroupsMovieRecIn = "select * from catalogTemp_usergroup where groupID in (select groupID_id from catalogTemp_movierecommendationwithingroup where recID_id = {0})"

list_comments_users_together = "select commentID, postID_id, commentUserID_id, commentBody, commentResponseID, createdAt, updatedAt, first_name," \
                               " last_name, username from catalogTemp_commentongroupmovierecommendation" \
                               " f inner join auth_user a on a.id = f.commentUserID_id where postID_id  = {0}"
list_comments_users_group_together = "select commentID, postID_id, commentUserID_id, commentBody, commentResponseID, f.createdAt, f.updatedAt, first_name," \
                               " last_name, username, groupID_id, groupName, groupDesc from catalogTemp_commentongroupmovierecommendation" \
                               " f inner join auth_user a on a.id = f.commentUserID_id" \
                                     " inner join catalogTemp_movierecommendationwithingroup c on f.postID_id = c.groupRecID" \
                                     " inner join catalogTemp_usergroup g on c.groupID_id = g.groupID" \
                                     " where postID_id  = {0}"
get_base_of_feed_query = "select recommenderUserID_id, groupRecID, a.createdAt, a.updatedAt, recID_id, recommendationDesc," \
            " recommenderRating, movieID_id, tvShowID_id, username, first_name," \
            " last_name from catalogTemp_movierecommendationwithingroup a " \
            "inner join catalogTemp_movierecommendation b on" \
            " a.recID_id = b.movieRecID inner join auth_user" \
            " c on b.recommenderUserID_id = c.id where groupID_id = "
get_base_of_feed_query_lo = "select recommenderUserID_id, groupRecID, a.createdAt, a.updatedAt, recID_id, recommendationDesc, recommenderRating, movieID_id, tvShowID_id, bookID_id, podcastID_id, episodeID_id username, first_name, last_name from (select * from catalogTemp_movierecommendationwithingroup where groupID_id = {0} and groupRecID < {1}) a inner join catalogTemp_movierecommendation b on a.recID_id = b.movieRecID inner join auth_user c on b.recommenderUserID_id = c.id order by -a.createdAt limit {2}"
get_base_of_feed_query_lo_no_min = "select recommenderUserID_id, groupRecID, a.createdAt, a.updatedAt, recID_id, recommendationDesc, recommenderRating, movieID_id, tvShowID_id, bookID_id, podcastID_id, episodeID_id, username, first_name, last_name from (select * from catalogTemp_movierecommendationwithingroup where groupID_id = {0}) a inner join catalogTemp_movierecommendation b on a.recID_id = b.movieRecID inner join auth_user c on b.recommenderUserID_id = c.id order by -a.createdAt limit {1}"


get_over_feed_query_new = "select recommenderUserID_id, groupRecID, a.createdAt, a.updatedAt, recID_id, recommendationDesc, recommenderRating, movieID_id, tvShowID_id, bookID_id, podcastID_id, episodeID_id, username, first_name, last_name " \
                          "from (select * from  catalogTemp_movierecommendationwithingroup where groupRecID < {0}" \
                          " and groupID_id in (select groupID_id from catalogTemp_groupmembers where userID_id={1}) and" \
                          " groupID_id not in (select groupID_id from catalogTemp_overallfeedexclusions where userID_id={2}))" \
                          " a inner join catalogTemp_movierecommendation b on a.recID_id = b.movieRecID inner join auth_user " \
                          "c on b.recommenderUserID_id = c.id group by recID_id order by -a.createdAt limit {3};"

get_over_feed_query_new_no_min = "select recommenderUserID_id, groupRecID, a.createdAt, a.updatedAt, recID_id, recommendationDesc, recommenderRating, movieID_id, tvShowID_id, bookID_id, podcastID_id, episodeID_id, username, first_name, last_name " \
                          "from (select * from  catalogTemp_movierecommendationwithingroup where" \
                          " groupID_id in (select groupID_id from catalogTemp_groupmembers where userID_id={0}) and" \
                          " groupID_id not in (select groupID_id from catalogTemp_overallfeedexclusions where userID_id={1}))" \
                          " a inner join catalogTemp_movierecommendation b on a.recID_id = b.movieRecID inner join auth_user " \
                          "c on b.recommenderUserID_id = c.id group by recID_id order by -a.createdAt limit {2};"

get_groupchat_photos_lo = "select groupchatPicID, fileName, S3Key, createdAt, groupID_id, userID_id from catalogTemp_groupchatpictures where groupID_id = {0} order by -groupchatPicID limit {1} offset {2}"
get_groupchat_photos_lo_max = "select groupchatPicID, fileName, S3Key, createdAt, groupID_id, userID_id from catalogTemp_groupchatpictures where groupID_id = {0}  and groupchatPicID < {1} order by -groupchatPicID limit {2} offset {3}"



"select groupID from catalogTemp_usergroup where groupID in (select groupID_id from catalogTemp_groupmembers where userID_id = {})"

get_users_who_endorse_post_query_depreciated = "select first_name, last_name, username from auth_user where id in (select endorserUserID_id " \
                          "from catalogTemp_endorsementsonmovierecsingroups where recID_id = {0})"

get_users_who_endorse_post_query = "select first_name, last_name, username from catalogTemp_endorsementsonmovierecsingroups " \
                                   "inner join auth_user a on a.id = endorserUserID_id where" \
                                   " recID_id = {0} and endorserUserID_id in (select userID_id from" \
                                   " catalogTemp_groupmembers where groupID_id in (select groupID from" \
                                   " catalogTemp_groupmembers a inner join catalogTemp_usergroup b " \
                                   "on a.groupID_id= b.groupID where a.userID_id = {1}));"

"select groupID_id where userID_id = {}" "select groupID_id where recID_id and groupID_id in ()"

group_info_query = "select a.groupRecID, a.groupID_id, b.groupName, S3Key from catalogTemp_movierecommendationwithingroup a inner join catalogTemp_usergroup b on a.groupID_id = b.groupID left join (select MAX(createdAt)" \
                   " as f, S3Key, groupID_id from catalogTemp_groupprofilepictures group by groupID_id) c on c.groupID_id = a.groupID_id where recID_id = {0}"

get_base_of_rankings_list = "select rankingItemID, rankingInList, rankingsDescription, " \
                            "movieID_id, movieID_id, rankingList_id, tvShowID_id from catalogTemp_rankingsitems where rankingList_id = {0}"