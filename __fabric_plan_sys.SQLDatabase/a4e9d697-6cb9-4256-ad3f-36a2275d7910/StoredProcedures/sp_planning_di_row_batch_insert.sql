
                                  CREATE PROCEDURE [a4e9d697-6cb9-4256-ad3f-36a2275d7910].[sp_planning_di_row_batch_insert] 
                                  @InputData as nvarchar(max),
                                  @createdBy as nvarchar(128),
                                  @updatedBy as nvarchar(128),
                                  @createdAt as int,
                                  @updatedAt as int
                                  AS
                                  BEGIN
                                  SET NOCOUNT ON;
                                  DECLARE @sql NVARCHAR(MAX) = '';
                                  DECLARE @currentTimeString NVARCHAR(50) = CONVERT(NVARCHAR(50), SYSDATETIME(), 121);
                                  DECLARE @TempTableName NVARCHAR(128) = '#CR_INSERT_TEMP' + REPLACE(REPLACE(REPLACE(REPLACE(@currentTimeString, '-', ''), ':', ''),' ',''),'.','');
                                  
                                      -- Create a temporary table to hold the JSON data
                                      SET @sql = N'
                                          CREATE TABLE [a4e9d697-6cb9-4256-ad3f-36a2275d7910].' + QUOTENAME(@TempTableName) + N' (
                                              id varchar(255),
                                              visualId int,
                                              name varchar(255),
                                              rowMeta nvarchar(max),
                                              visualRowConfigId int,
                                              rowPath nvarchar(max),
                                              createdBy nvarchar(128),
                                              updatedBy nvarchar(128),
                                              createdAt int,
                                              updatedAt int
                                          );
                                      ';

                                      
                                  
                                    -- Insert data into the temporary table using dynamic SQL
                                      SET @sql =  @sql + N'
                                          INSERT INTO [a4e9d697-6cb9-4256-ad3f-36a2275d7910].' + QUOTENAME(@TempTableName) + N'
                                          (id, name, rowMeta, visualRowConfigId, rowPath,  visualId, createdBy, updatedBy, createdAt, updatedAt)
                                          SELECT *,@createdBy, @updatedBy, @createdAt, @updatedAt
                                          FROM OPENJSON(@InputData)
                                          WITH (
                                          "id" varchar(255) ''$.i'',
                                          "name" varchar(255) ''$.n'',
                                          "rowMeta" nvarchar(max) ''$.rm'',
                                          "visualRowConfigId" int ''$.vrci'',
                                          "rowPath" nvarchar(max) ''$.rp'',
                                          "visualId" int ''$.vi''
                                          );
                                      ';
                                  
                                      SET @sql = @sql + 'INSERT INTO [a4e9d697-6cb9-4256-ad3f-36a2275d7910].data_input_row (id, name, rowMeta, visualRowConfigId, rowPath,  visualId, createdBy, updatedBy, createdAt, updatedAt)
                                      SELECT temp.id, temp.name, temp.rowMeta, temp.visualRowConfigId, temp.rowPath, temp.visualId, createdBy, updatedBy, createdAt, updatedAt FROM [a4e9d697-6cb9-4256-ad3f-36a2275d7910].' + @TempTableName + ' as temp;';
                                      
                                      SET @sql = @sql + N'DROP TABLE [a4e9d697-6cb9-4256-ad3f-36a2275d7910].' + @TempTableName + ';';
                                  
                                      EXEC sp_executesql @sql, N'
                                      @InputData NVARCHAR(MAX),
                                      @createdBy nvarchar(128),
                                      @updatedBy nvarchar(128),
                                      @createdAt INT,
                                      @updatedAt INT',
                                      @InputData,
                                      @createdBy,
                                      @updatedBy,
                                      @createdAt,
                                      @updatedAt;
                                      SET NOCOUNT OFF;
                                  
                                  END

GO

